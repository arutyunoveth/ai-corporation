from datetime import datetime

from pydantic import Field

from src.shared.enums import RequirementExtractionStatus
from src.shared.types.common import APIModel


class BuildRequirementExtractionRequest(APIModel):
    document_set_id: str


class RequirementSourceLinkResponse(APIModel):
    source_ref: str
    created_at: datetime


class RequirementExtractionRecordResponse(APIModel):
    requirement_extraction_id: str
    requirement_extraction_set_id: str
    requirement_code: str
    requirement_text: str
    requirement_group: str
    created_at: datetime
    updated_at: datetime
    source_links: list[RequirementSourceLinkResponse] = Field(default_factory=list)


class RequirementExtractionSetResponse(APIModel):
    requirement_extraction_set_id: str
    document_set_id: str
    extraction_status: RequirementExtractionStatus
    created_at: datetime
    updated_at: datetime
    records: list[RequirementExtractionRecordResponse] = Field(default_factory=list)
