from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class PublicHealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    mode: Literal["public"] = "public"
    version: str = "1.0.0"


class PublicVersionResponse(BaseModel):
    name: str = "Ledger Normalization API"
    version: str = "1.0.0"
    breaking: bool = False


class BillsNormalizeRequest(BaseModel):
    bills: list[dict[str, Any]] = Field(default_factory=list)


class NormalizedBillPublic(BaseModel):
    id: str | None = None
    name: str | None = None
    amount: float | None = None
    frequency: str | None = None
    due_day: int | None = None
    status: str | None = None
    confidence: float | None = None
    category: str | None = None


class BillsNormalizeResponse(BaseModel):
    normalized: list[NormalizedBillPublic] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BillsAnalyzeRequest(BaseModel):
    bills: list[dict[str, Any]] = Field(default_factory=list)
    reference_date: date | None = None


class AnalyzedBill(BaseModel):
    id: str | None = None
    name: str | None = None
    status: Literal["paid", "unpaid", "overdue", "unknown"] = "unknown"
    days_late: int | None = None
    due_date: date | None = None


class BillsAnalyzeSummary(BaseModel):
    total_monthly: float = 0.0
    overdue_count: int = 0
    upcoming_7_days: int = 0


class BillsAnalyzeResponse(BaseModel):
    summary: BillsAnalyzeSummary
    bills: list[AnalyzedBill] = Field(default_factory=list)


class LedgerSummarizeRequest(BaseModel):
    bills: list[dict[str, Any]] = Field(default_factory=list)
    period: Literal["monthly"] = "monthly"


class LedgerSummarizeResponse(BaseModel):
    period: str = "monthly"
    totals: dict[str, float] = Field(default_factory=dict)
    projected_cash_flow: float = 0.0
