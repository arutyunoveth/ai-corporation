from datetime import datetime

from pydantic import Field

from src.shared.enums import ArchiveExportFormat, ArchiveExportItemRole, ArchiveExportStatus
from src.shared.types.common import APIModel


class BuildArchiveExportRequest(APIModel):
    deal_id: str
    deal_closure_set_id: str
    export_format: ArchiveExportFormat = ArchiveExportFormat.MANIFEST
    mark_exported: bool = False
    item_roles: list[ArchiveExportItemRole] = Field(default_factory=list)


class ArchiveExportItemResponse(APIModel):
    artifact_ref: str
    item_role: ArchiveExportItemRole
    created_at: datetime


class ArchiveExportRecordResponse(APIModel):
    archive_export_id: str
    archive_export_set_id: str
    export_manifest_json: dict
    export_format: ArchiveExportFormat
    created_at: datetime
    updated_at: datetime
    items: list[ArchiveExportItemResponse]


class ArchiveExportSetResponse(APIModel):
    archive_export_set_id: str
    deal_id: str
    deal_closure_set_id: str
    export_status: ArchiveExportStatus
    created_at: datetime
    updated_at: datetime
    records: list[ArchiveExportRecordResponse]
