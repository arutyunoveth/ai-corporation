from datetime import datetime

from src.shared.enums import BidDocumentCollectionStatus, BidDocumentRowStatus
from src.shared.types.common import APIModel


class BuildBidDocumentCollectionRequest(APIModel):
    deal_id: str
    document_requirement_set_id: str
    ceo_approval_set_id: str


class BidDocumentCollectionBindingResponse(APIModel):
    source_object_type: str
    source_object_ref: str
    created_at: datetime


class BidDocumentCollectionRowResponse(APIModel):
    requirement_row_ref: str
    artifact_ref: str | None
    collection_status: BidDocumentRowStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BidDocumentCollectionSetResponse(APIModel):
    bid_document_collection_set_id: str
    deal_id: str
    document_requirement_set_id: str
    ceo_approval_set_id: str
    collection_status: BidDocumentCollectionStatus
    created_at: datetime
    updated_at: datetime
    rows: list[BidDocumentCollectionRowResponse]
    bindings: list[BidDocumentCollectionBindingResponse]
