from fastapi import APIRouter, Query, status

from src.modules.dashboard_snapshots.schemas import (
    BuildDashboardSnapshotRequest,
    DashboardMetricRecordResponse,
    DashboardSnapshotRecordResponse,
    DashboardSnapshotSetResponse,
)
from src.modules.dashboard_snapshots.service import (
    build_dashboard_snapshot,
    get_dashboard_snapshot_record,
    get_dashboard_snapshot_set,
    list_dashboard_snapshot_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import DashboardScopeType

router = APIRouter(tags=["dashboards"])


def _to_metric_response(item) -> DashboardMetricRecordResponse:
    return DashboardMetricRecordResponse.model_validate(item)


def _to_record_response(result: tuple) -> DashboardSnapshotRecordResponse:
    record, metrics = result
    return DashboardSnapshotRecordResponse(
        dashboard_snapshot_id=record.dashboard_snapshot_id,
        dashboard_snapshot_set_id=record.dashboard_snapshot_set_id,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        metrics=[_to_metric_response(item) for item in metrics],
    )


def _to_set_response(result: tuple) -> DashboardSnapshotSetResponse:
    snapshot_set, records = result
    return DashboardSnapshotSetResponse(
        dashboard_snapshot_set_id=snapshot_set.dashboard_snapshot_set_id,
        scope_type=snapshot_set.scope_type,
        scope_ref=snapshot_set.scope_ref,
        snapshot_status=snapshot_set.snapshot_status,
        created_at=snapshot_set.created_at,
        updated_at=snapshot_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/dashboards/build", response_model=DashboardSnapshotSetResponse, status_code=status.HTTP_201_CREATED)
def build_dashboard_snapshot_route(payload: BuildDashboardSnapshotRequest, session: DBSession) -> DashboardSnapshotSetResponse:
    snapshot_set = build_dashboard_snapshot(session, payload)
    return _to_set_response(get_dashboard_snapshot_set(session, snapshot_set.dashboard_snapshot_set_id))


@router.get("/dashboards/{dashboard_snapshot_set_id}", response_model=DashboardSnapshotSetResponse)
def get_dashboard_snapshot_set_route(dashboard_snapshot_set_id: str, session: DBSession) -> DashboardSnapshotSetResponse:
    return _to_set_response(get_dashboard_snapshot_set(session, dashboard_snapshot_set_id))


@router.get("/dashboards", response_model=list[DashboardSnapshotSetResponse])
def list_dashboard_snapshot_sets_route(
    session: DBSession,
    scope_type: DashboardScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[DashboardSnapshotSetResponse]:
    return [_to_set_response(item) for item in list_dashboard_snapshot_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/dashboards/records/{dashboard_snapshot_id}", response_model=DashboardSnapshotRecordResponse)
def get_dashboard_snapshot_record_route(dashboard_snapshot_id: str, session: DBSession) -> DashboardSnapshotRecordResponse:
    return _to_record_response(get_dashboard_snapshot_record(session, dashboard_snapshot_id))
