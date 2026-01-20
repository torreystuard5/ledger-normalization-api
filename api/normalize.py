"""Normalization helpers for API responses (read-only)."""

from __future__ import annotations

from typing import Any, Dict, Optional

_TRUE_STRINGS = {"paid", "p", "yes", "true", "1", "done", "complete", "completed", "x"}
_FALSE_STRINGS = {"unpaid", "no", "false", "0", "none", ""}


def _as_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def derive_paid(status: Any, actual_paid: Any) -> bool:
    if isinstance(actual_paid, bool):
        return actual_paid

    s = _as_str(status)
    if s is None:
        return False

    s_low = s.lower()
    if s_low in _TRUE_STRINGS:
        return True
    if s_low in _FALSE_STRINGS:
        return False
    if "paid" in s_low and "unpaid" not in s_low:
        return True
    return False


def normalize_bill(raw: Dict[str, Any]) -> Dict[str, Any]:
    bill_id = raw.get("id") or ""
    paid = derive_paid(raw.get("status"), raw.get("actual_paid"))

    sheet = raw.get("sheet") or raw.get("_sheet")
    row = raw.get("row") or raw.get("_row")

    return {
        "id": bill_id,
        "name": raw.get("name"),
        "amount": raw.get("amount"),
        "frequency": raw.get("frequency"),
        "category": raw.get("category"),
        "status": raw.get("status"),
        "paid": paid,
        "actual_paid": paid,
        "paid_amount": raw.get("paid_amount"),
        "paid_date": raw.get("paid_date"),
        "due_date": raw.get("due_date"),
        "note": raw.get("note"),
        "sheet": sheet,
        "row": row,
    }
