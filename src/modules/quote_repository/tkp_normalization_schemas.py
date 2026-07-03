from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ComplianceStatus = Literal["unknown", "matched", "equivalent", "missing", "non_compliant", "needs_review"]
TKPNormalizationStatus = Literal["parsed", "needs_review", "failed", "unsupported_format"]
TKPParserMode = Literal["deterministic", "llm", "hybrid"]


class NormalizedTKPLineItem(BaseModel):
    item_index: int = Field(ge=1)
    item_name: str = Field(min_length=1)
    manufacturer: str | None = None
    brand: str | None = None
    model: str | None = None
    article: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    vat_included: bool | None = None
    delivery_time_days: int | None = None
    compliance_status: ComplianceStatus = "needs_review"
    comments: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class NormalizedTKPQuote(BaseModel):
    supplier_label: str = Field(min_length=1)
    supplier_id: str | None = None
    source_file: str = Field(min_length=1)
    normalization_status: TKPNormalizationStatus
    quote_date: str | None = None
    valid_until: str | None = None
    currency_code: str = "RUB"
    vat_included: bool | None = None
    vat_rate: float | None = None
    total_amount: float | None = None
    total_amount_without_vat: float | None = None
    delivery_cost: float | None = None
    delivery_time_days: int | None = None
    payment_terms: str | None = None
    warranty_months: int | None = None
    availability: str | None = None
    includes_delivery: bool | None = None
    includes_installation: bool | None = None
    certificates_available: bool | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    line_items: list[NormalizedTKPLineItem] = Field(default_factory=list)
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    fields_needing_review: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    parser_mode: TKPParserMode
    human_review_required: bool = True


class NormalizedTKPQuoteBatch(BaseModel):
    quotes: list[NormalizedTKPQuote] = Field(default_factory=list)
