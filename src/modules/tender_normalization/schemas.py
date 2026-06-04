from datetime import datetime

from pydantic import Field

from src.shared.enums import TenderNormalizationStatus
from src.shared.types.common import APIModel


class BuildTenderNormalizationRequest(APIModel):
    tender_import_event_id: str


class TenderNormalizationLinkResponse(APIModel):
    customer_id: str | None
    deal_id: str | None
    created_at: datetime


class TenderNormalizationRecordResponse(APIModel):
    tender_normalization_id: str
    tender_normalization_set_id: str
    normalized_procurement_number: str | None
    normalized_title: str
    normalized_customer_name: str
    normalized_deadline_at: datetime | None
    created_at: datetime
    updated_at: datetime
    links: list[TenderNormalizationLinkResponse] = Field(default_factory=list)


class TenderNormalizationSetResponse(APIModel):
    tender_normalization_set_id: str
    tender_import_event_id: str
    normalization_status: TenderNormalizationStatus
    created_at: datetime
    updated_at: datetime
    records: list[TenderNormalizationRecordResponse] = Field(default_factory=list)
