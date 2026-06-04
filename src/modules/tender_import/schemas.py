from datetime import datetime

from pydantic import Field

from src.shared.enums import TenderImportRunStatus
from src.shared.types.common import APIModel


class TenderImportEventInput(APIModel):
    raw_procurement_number: str | None = None
    source_url: str | None = None
    payload_json: dict = Field(default_factory=dict)


class CreateTenderImportRunRequest(APIModel):
    source_type: str
    source_ref: str
    events: list[TenderImportEventInput] = Field(default_factory=list)


class TenderImportPayloadResponse(APIModel):
    payload_json: dict
    payload_hash: str
    created_at: datetime


class TenderImportEventResponse(APIModel):
    tender_import_event_id: str
    tender_import_run_id: str
    raw_procurement_number: str | None
    source_url: str | None
    created_at: datetime
    updated_at: datetime
    payload: TenderImportPayloadResponse


class TenderImportRunResponse(APIModel):
    tender_import_run_id: str
    source_type: str
    source_ref: str
    run_status: TenderImportRunStatus
    created_at: datetime
    updated_at: datetime
    events: list[TenderImportEventResponse]
