from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(tags=["public"])


# -------------------------
# Models
# -------------------------

class Bill(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    frequency: Optional[str] = None
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    status: Optional[str] = None
    note: Optional[str] = None


class NormalizeRequest(BaseModel):
    bills: List[Bill]


class NormalizeResponse(BaseModel):
    normalized: List[Bill]


class AnalyzeRequest(BaseModel):
    bills: List[Bill]


class AnalyzeResponse(BaseModel):
    count: int
    totals: Dict[str, float]
    by_category: Dict[str, Dict[str, float]]
    by_status: Dict[str, Dict[str, float]]
    normalized: List[Bill]


class SummarizeRequest(BaseModel):
    bills: List[Bill]


class SummarizeResponse(BaseModel):
    count: int
    totals: Dict[str, float]
    by_category: Dict[str, Dict[str, float]]
    by_status: Dict[str, Dict[str, float]]


# -------------------------
# Helpers
# -------------------------

def normalize_bill(b: Bill) -> Bill:
    nb = Bill(**b.dict())

    if nb.name:
        nb.name = " ".join(nb.name.split())

    if nb.amount is not None:
        try:
            nb.amount = float(nb.amount)
        except Exception:
            nb.amount = None

    if nb.due_day is not None:
        if not (1 <= nb.due_day <= 31):
            nb.due_day = None

    if not nb.category:
        nb.category = "uncategorized"

    if not nb.frequency:
        nb.frequency = "monthly"

    if not nb.status:
        if nb.due_day is None:
            nb.status = "unknown"
        else:
            today = datetime.now().day
            if nb.due_day < today:
                nb.status = "overdue"
            elif nb.due_day == today:
                nb.status = "due"
            else:
                nb.status = "upcoming"

    return nb


def rollups(bills: List[Bill]):
    totals = {"amount": 0.0}
    by_category: Dict[str, Dict[str, float]] = {}
    by_status: Dict[str, Dict[str, float]] = {}

    for b in bills:
        amt = b.amount or 0.0
        totals["amount"] += amt

        cat = b.category or "uncategorized"
        st = b.status or "unknown"

        by_category.setdefault(cat, {"amount": 0.0, "count": 0})
        by_category[cat]["amount"] += amt
        by_category[cat]["count"] += 1

        by_status.setdefault(st, {"amount": 0.0, "count": 0})
        by_status[st]["amount"] += amt
        by_status[st]["count"] += 1

    totals["amount"] = round(totals["amount"], 2)
    for v in by_category.values():
        v["amount"] = round(v["amount"], 2)
    for v in by_status.values():
        v["amount"] = round(v["amount"], 2)

    return totals, by_category, by_status


# -------------------------
# Public Endpoints
# -------------------------

@router.post("/normalize", response_model=NormalizeResponse)
def normalize(req: NormalizeRequest):
    normalized = [normalize_bill(b) for b in req.bills]
    return {"normalized": normalized}


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    normalized = [normalize_bill(b) for b in req.bills]
    totals, by_category, by_status = rollups(normalized)

    return {
        "count": len(normalized),
        "totals": totals,
        "by_category": by_category,
        "by_status": by_status,
        "normalized": normalized,
    }


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(req: SummarizeRequest):
    normalized = [normalize_bill(b) for b in req.bills]
    totals, by_category, by_status = rollups(normalized)

    return {
        "count": len(normalized),
        "totals": totals,
        "by_category": by_category,
        "by_status": by_status,
    }
