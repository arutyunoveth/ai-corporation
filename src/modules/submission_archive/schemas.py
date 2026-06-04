from datetime import datetime

from pydantic import Field

from src.shared.enums import SubmissionArchiveItemRole, SubmissionArchiveStatus
from src.shared.types.common import APIModel


class BuildSubmissionArchiveRequest(APIModel):
    deal_id: str
    bid_package_set_id: str


class SubmissionArchiveItemResponse(APIModel):
    artifact_ref: str
    item_role: SubmissionArchiveItemRole
    created_at: datetime


class SubmissionArchiveRecordResponse(APIModel):
    submission_archive_id: str
    submission_archive_set_id: str
    archive_manifest_json: dict
    proof_summary: str
    created_at: datetime
    updated_at: datetime
    items: list[SubmissionArchiveItemResponse] = Field(default_factory=list)


class SubmissionArchiveSetResponse(APIModel):
    submission_archive_set_id: str
    deal_id: str
    archive_status: SubmissionArchiveStatus
    created_at: datetime
    updated_at: datetime
    records: list[SubmissionArchiveRecordResponse] = Field(default_factory=list)
