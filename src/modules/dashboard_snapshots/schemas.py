from datetime import datetime

from src.shared.enums import DashboardScopeType, DashboardSnapshotStatus
from src.shared.types.common import APIModel


class BuildDashboardSnapshotRequest(APIModel):
    scope_type: DashboardScopeType
    scope_ref: str


class DashboardMetricRecordResponse(APIModel):
    metric_code: str
    metric_value_numeric: float | None
    metric_value_text: str | None
    created_at: datetime


class DashboardSnapshotRecordResponse(APIModel):
    dashboard_snapshot_id: str
    dashboard_snapshot_set_id: str
    summary_text: str
    created_at: datetime
    updated_at: datetime
    metrics: list[DashboardMetricRecordResponse]


class DashboardSnapshotSetResponse(APIModel):
    dashboard_snapshot_set_id: str
    scope_type: DashboardScopeType
    scope_ref: str
    snapshot_status: DashboardSnapshotStatus
    created_at: datetime
    updated_at: datetime
    records: list[DashboardSnapshotRecordResponse]
