from datetime import datetime

from src.shared.enums import QuoteStatus
from src.shared.types.common import APIModel


class RegisterQuoteRequest(APIModel):
    deal_id: str
    supplier_id: str
    rfq_id: str
    supplier_thread_id: str
    quoted_amount: float
    currency_code: str
    quoted_at: datetime | None = None
    notes: str | None = None
    quote_status: QuoteStatus = QuoteStatus.RECEIVED
    artifact_refs: list[str] = []


class QuoteArtifactBindingResponse(APIModel):
    artifact_ref: str
    created_at: datetime


class QuoteResponse(APIModel):
    quote_id: str
    quote_set_id: str
    supplier_id: str
    rfq_id: str
    supplier_thread_id: str
    quote_status: QuoteStatus
    quoted_amount: float
    currency_code: str
    quoted_at: datetime
    notes: str | None
    created_at: datetime
    updated_at: datetime
    artifact_bindings: list[QuoteArtifactBindingResponse] = []


class QuoteSetResponse(APIModel):
    quote_set_id: str
    deal_id: str
    rfq_batch_id: str
    created_at: datetime
    quotes: list[QuoteResponse]
