from datetime import datetime

from src.shared.enums import RFQBatchStatus, RFQStatus
from src.shared.types.common import APIModel


class BuildRFQBatchRequest(APIModel):
    deal_id: str
    supplier_shortlist_id: str


class RFQRecordResponse(APIModel):
    rfq_id: str
    rfq_batch_id: str
    supplier_id: str
    subject: str
    body_text: str
    rfq_status: RFQStatus
    created_at: datetime
    updated_at: datetime
    artifact_refs: list[str] = []


class RFQBatchResponse(APIModel):
    rfq_batch_id: str
    deal_id: str
    supplier_shortlist_id: str
    batch_status: RFQBatchStatus
    created_at: datetime
    updated_at: datetime
    rfq_records: list[RFQRecordResponse]
