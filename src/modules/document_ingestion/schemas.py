from datetime import datetime

from pydantic import Field

from src.shared.enums import DocumentIngestionRunStatus, DocumentIngestionStatus, DocumentSetItemRole, DocumentSetType
from src.shared.types.common import APIModel


class DocumentSetItemInput(APIModel):
    artifact_ref: str = Field(min_length=1)
    item_role: DocumentSetItemRole
    source_file_name: str = Field(min_length=1)
    sort_order: int = 0


class CreateDocumentSetRequest(APIModel):
    deal_id: str = Field(min_length=1)
    intake_id: str = Field(min_length=1)
    set_type: DocumentSetType
    items: list[DocumentSetItemInput]


class CreateDocumentIngestionRunRequest(APIModel):
    run_status: DocumentIngestionRunStatus
    notes: str | None = None


class DocumentSetItemResponse(APIModel):
    artifact_ref: str
    item_role: DocumentSetItemRole
    source_file_name: str
    sort_order: int
    created_at: datetime


class DocumentIngestionRunResponse(APIModel):
    ingestion_run_id: str
    document_set_id: str
    run_status: DocumentIngestionRunStatus
    started_at: datetime
    finished_at: datetime | None
    notes: str | None


class DocumentSetResponse(APIModel):
    document_set_id: str
    deal_id: str
    intake_id: str
    set_type: DocumentSetType
    ingestion_status: DocumentIngestionStatus
    item_count: int
    created_at: datetime
    updated_at: datetime
    items: list[DocumentSetItemResponse]
    runs: list[DocumentIngestionRunResponse]


class CreateDocumentSetResponse(APIModel):
    document_set_id: str
    ingestion_status: DocumentIngestionStatus
    item_count: int

