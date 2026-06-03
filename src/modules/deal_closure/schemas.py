from datetime import datetime

from src.shared.enums import DealClosureCode, DealClosureStatus
from src.shared.types.common import APIModel


class BuildDealClosureRequest(APIModel):
    deal_id: str
    outcome_intake_set_id: str
    execution_command_set_id: str


class CloseDealRequest(APIModel):
    deal_closure_set_id: str
    summary_text: str | None = None
    closed_at: datetime | None = None


class DealArchiveSnapshotResponse(APIModel):
    archive_snapshot_id: str
    deal_closure_set_id: str
    snapshot_manifest_json: dict
    created_at: datetime


class DealClosureRecordResponse(APIModel):
    deal_closure_id: str
    deal_closure_set_id: str
    closure_code: DealClosureCode
    summary_text: str
    closed_at: datetime
    created_at: datetime
    updated_at: datetime


class DealClosureSetResponse(APIModel):
    deal_closure_set_id: str
    deal_id: str
    outcome_intake_set_id: str
    execution_command_set_id: str
    closure_status: DealClosureStatus
    created_at: datetime
    updated_at: datetime
    records: list[DealClosureRecordResponse]
    archive_snapshots: list[DealArchiveSnapshotResponse]
