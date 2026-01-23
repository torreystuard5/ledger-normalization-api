from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field


# Always export `router` so `from api.public_router import router` works.
router = APIRouter()


# -----------------------------
# Auth (RapidAPI style)
# -----------------------------
def require_rapidapi_key(x_rapidapi_key: Optional[str]) -> None:
    # RapidAPI injects X-RapidAPI-Key automatically.
    # We only require it to exist (do not validate contents here).
    if not x_rapidapi_key or not x_rapidapi_key.strip():
        raise HTTPException(status_code=401, detail="Missing or invalid RapidAPI key.")


# -----------------------------
# Models (self-contained, so imports can't break startup)
# -----------------------------
class BillIn(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1)
    amount: Optional[float] = None
    category: Optional[str] = None
    frequency: Optional[str] = None
    due_day: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


class BillsNormalizeRequest(BaseModel):
    bills: List[BillIn]


class BillsNormalizeResponse(BaseModel):
    normalized: List[Dict[str, Any]]


class LedgerSummarizeRequest(BaseModel):
    bills: List[BillIn]


class LedgerSummarizeResponse(BaseModel):
    totals: Dict[str, float]
    count: int
    by_category: Dict[str, float]
    by_status: Dict[str, int]


# -----------------------------
# Optional: use your real normalizer if available
# -----------------------------
try:
    # If your project already has this function, we use it.
    from api.normalize import normalize_bill as _normalize_bill  # type: ignore
except Exception:  # pragma: no cover
    _normalize_bill = None  # type: ignore


def _basic_normalize(b: BillIn, idx: int) -> Dict[str, Any]:
    # Minimal fallback (keeps API usable even if normalize module is missing)
    return {
        "id": b.id or f"bill_{idx+1}",
        "name": b.name,
        "amount": float(b.amount) if b.amount is not None else 0.0,
        "frequency": b.frequency or "",
        "due_day": b.due_day or "",
        "status": b.status or "unpaid",
        "confidence": 0.5,
        "category": (b.category or "").strip().lower() or "uncategorized",
    }


def _normalize(b: BillIn, idx: int) -> Dict[str, Any]:
    if _normalize_bill is None:
        return _basic_normalize(b, idx)

    # Try your real normalizer. If it errors on an input, fall back cleanly.
    try:
        raw = b.model_dump()
        out = _normalize_bill(raw)  # expects dict in many codebases
        if isinstance(out, dict):
            return out
        # If it returns a pydantic model or something else, coerce
        return dict(out)
    except Exception:
        return _basic_normalize(b, idx)


# -----------------------------
# Routes
# -----------------------------
@router.post("/v1/bills/normalize", response_model=BillsNormalizeResponse)
def bills_normalize(
    payload: BillsNormalizeRequest,
    x_rapidapi_key: Optional[str] = Header(default=None, alias="X-RapidAPI-Key"),
):
    require_rapidapi_key(x_rapidapi_key)
    normalized = [_normalize(b, i) for i, b in enumerate(payload.bills)]
    return {"normalized": normalized}


@router.post("/v1/ledger/summarize", response_model=LedgerSummarizeResponse)
def ledger_summarize(
    payload: LedgerSummarizeRequest,
    x_rapidapi_key: Optional[str] = Header(default=None, alias="X-RapidAPI-Key"),
):
    require_rapidapi_key(x_rapidapi_key)

    totals: Dict[str, float] = {"total_amount": 0.0}
    by_category: Dict[str, float] = {}
    by_status: Dict[str, int] = {}

    for i, b in enumerate(payload.bills):
        n = _normalize(b, i)

        amt = float(n.get("amount") or 0.0)
        totals["total_amount"] += amt

        cat = str(n.get("category") or "uncategorized")
        by_category[cat] = by_category.get(cat, 0.0) + amt

        status = str(n.get("status") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1

    return {
        "totals": totals,
        "count": len(payload.bills),
        "by_category": by_category,
        "by_status": by_status,
    }
