from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from api.normalize import normalize_bill
from api.public_models import (
    BillsAnalyzeRequest,
    BillsAnalyzeResponse,
    BillsAnalyzeSummary,
    BillsNormalizeRequest,
    BillsNormalizeResponse,
    LedgerSummarizeRequest,
    LedgerSummarizeResponse,
    PublicHealthResponse,
    PublicVersionResponse,
)


def require_public_auth(
    # RapidAPI gateway injects these:
    # - X-RapidAPI-Key (consumer key)
    # - X-RapidAPI-Host (the RapidAPI host for your API)
    x_rapidapi_key: str | None = Header(default=None),
    x_rapidapi_host: str | None = Header(default=None),
    # Optional: your own private backdoor for direct calls (ONLY if you set PLC_PUBLIC_API_KEY)
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """
    RapidAPI-only auth strategy (recommended for marketplace):
    - If PLC_PUBLIC_ALLOW_ANON=1 -> allow without headers (dev only).
    - Otherwise:
        ✅ Allow ONLY if request came through RapidAPI gateway:
           requires BOTH X-RapidAPI-Key and X-RapidAPI-Host.
        ✅ Optionally allow direct/internal calls ONLY if PLC_PUBLIC_API_KEY is set
           and the request provides X-API-Key matching it.
        ❌ Block everything else.
    """
    # Dev-only bypass
    if str(os.environ.get("PLC_PUBLIC_ALLOW_ANON", "")).strip() == "1":
        return

    # 1) RapidAPI gateway path: require BOTH headers
    rk = (x_rapidapi_key or "").strip()
    rh = (x_rapidapi_host or "").strip()
    if rk and rh:
        return

    # 2) Optional internal direct-call path (ONLY if you set PLC_PUBLIC_API_KEY)
    expected = str(os.environ.get("PLC_PUBLIC_API_KEY", "")).strip()
    provided_internal = (x_api_key or "").strip()
    if expected and provided_internal == expected:
        return

    # 3) Block everything else
    raise HTTPException(
        status_code=401,
        detail="Unauthorized (RapidAPI-only). Use RapidAPI gateway or a valid X-API-Key if enabled.",
    )


# Apply auth ONCE for all /v1/* endpoints
public_v1_router = APIRouter(
    prefix="/v1",
    dependencies=[Depends(require_public_auth)],
)


@public_v1_router.get("/health", response_model=PublicHealthResponse)
def health() -> dict[str, Any]:
    return {"status": "ok", "mode": "public", "version": "1.0.0"}


@public_v1_router.get("/version", response_model=PublicVersionResponse)
def version() -> dict[str, Any]:
    return {"name": "Ledger Normalization API", "version": "1.0.0", "breaking": False}


def _safe_float(x: Any) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def _infer_due_day(obj: Any) -> int | None:
    if not isinstance(obj, dict):
        return None
    for key in ("due_day", "dueDay", "due_date_day"):
        v = obj.get(key)
        if isinstance(v, int) and 1 <= v <= 31:
            return v
        if isinstance(v, str) and v.isdigit():
            i = int(v)
            if 1 <= i <= 31:
                return i
    due_date = obj.get("due_date") or obj.get("dueDate")
    if isinstance(due_date, str) and len(due_date) >= 10:
        try:
            d = datetime.strptime(due_date[:10], "%Y-%m-%d").date()
            return d.day
        except Exception:
            return None
    return None


def _status_from(nb: dict[str, Any]) -> str:
    for k in ("paid", "actual_paid", "is_paid"):
        if k in nb:
            try:
                return "paid" if bool(nb.get(k)) else "unpaid"
            except Exception:
                pass
    st = (nb.get("status") or "").strip().lower()
    if st in ("paid", "unpaid", "overdue"):
        return st
    return "unknown"


def _model_to_dict(m: Any) -> dict[str, Any]:
    """
    Pydantic v2: model_dump()
    Pydantic v1: dict()
    """
    if hasattr(m, "model_dump"):
        return m.model_dump()  # type: ignore[attr-defined]
    if hasattr(m, "dict"):
        return m.dict()  # type: ignore[attr-defined]
    return dict(m) if isinstance(m, dict) else {}


@public_v1_router.post(
    "/bills/normalize",
    response_model=BillsNormalizeResponse,
)
def bills_normalize(req: BillsNormalizeRequest) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    warnings: list[str] = []

    for i, b in enumerate(req.bills or []):
        if not isinstance(b, dict):
            warnings.append(f"Item {i} ignored (not an object)")
            continue
        try:
            nb = normalize_bill(b)
            if not isinstance(nb, dict):
                nb = dict(nb)  # best effort
        except Exception as e:
            warnings.append(f"Item {i} normalize failed: {e}")
            continue

        out = {
            "id": nb.get("id") or b.get("id") or f"bill_{i+1}",
            "name": nb.get("name") or b.get("name"),
            "amount": _safe_float(nb.get("amount") if "amount" in nb else b.get("amount")),
            "frequency": nb.get("frequency") or b.get("frequency"),
            "due_day": _infer_due_day(nb) or _infer_due_day(b),
            "status": _status_from(nb),
            "confidence": nb.get("confidence", 0.85),
            "category": nb.get("category") or b.get("category"),
        }
        normalized.append(out)

    return {"normalized": normalized, "warnings": warnings}


@public_v1_router.post(
    "/bills/analyze",
    response_model=BillsAnalyzeResponse,
)
def bills_analyze(req: BillsAnalyzeRequest) -> dict[str, Any]:
    ref = req.reference_date or date.today()

    norm = bills_normalize(BillsNormalizeRequest(bills=req.bills)).get("normalized", [])
    analyzed: list[dict[str, Any]] = []

    total_monthly = 0.0
    overdue_count = 0
    upcoming_7 = 0

    for i, nb in enumerate(norm):
        name = nb.get("name")
        bill_id = nb.get("id") or f"bill_{i+1}"
        amt = _safe_float(nb.get("amount")) or 0.0
        due_day = nb.get("due_day")

        status = (nb.get("status") or "unknown").lower()
        due_date = None
        days_late = None

        if isinstance(due_day, int) and 1 <= due_day <= 31:
            try:
                # Use reference month/year
                if due_day <= 28:
                    due_date = date(ref.year, ref.month, due_day)
                else:
                    # last day of month approximation for 29-31
                    next_month = date(ref.year + (ref.month // 12), ((ref.month % 12) + 1), 1)
                    due_date = next_month - timedelta(days=1)
            except Exception:
                due_date = None

        if status == "paid":
            pass
        elif due_date is not None:
            if ref > due_date:
                status = "overdue"
                days_late = (ref - due_date).days
            else:
                status = "unpaid"
                if (due_date - ref).days <= 7:
                    upcoming_7 += 1

        if status == "overdue":
            overdue_count += 1

        total_monthly += amt

        analyzed.append(
            {
                "id": bill_id,
                "name": name,
                "status": status if status in ("paid", "unpaid", "overdue") else "unknown",
                "days_late": days_late,
                "due_date": due_date,
            }
        )

    summary = BillsAnalyzeSummary(
        total_monthly=round(total_monthly, 2),
        overdue_count=overdue_count,
        upcoming_7_days=upcoming_7,
    )

    return {"summary": _model_to_dict(summary), "bills": analyzed}


@public_v1_router.post(
    "/ledger/summarize",
    response_model=LedgerSummarizeResponse,
)
def ledger_summarize(req: LedgerSummarizeRequest) -> dict[str, Any]:
    norm = bills_normalize(BillsNormalizeRequest(bills=req.bills)).get("normalized", [])

    totals: dict[str, float] = {}
    projected_cash_flow = 0.0

    for nb in norm:
        cat = (nb.get("category") or "uncategorized").strip().lower()
        amt = _safe_float(nb.get("amount")) or 0.0
        totals[cat] = round(totals.get(cat, 0.0) + amt, 2)
        projected_cash_flow -= amt

    return {
        "period": req.period,
        "totals": totals,
        "projected_cash_flow": round(projected_cash_flow, 2),
    }
