from fastapi import APIRouter, Query, status

from src.modules.procedure_monitor.schemas import (
    BuildProcedureMonitorRequest,
    ProcedureMonitorAlertResponse,
    ProcedureMonitorEventResponse,
    ProcedureMonitorRecordResponse,
    ProcedureMonitorSetResponse,
    RegisterProcedureMonitorEventRequest,
)
from src.modules.procedure_monitor.service import (
    build_procedure_monitor,
    get_procedure_monitor_record,
    get_procedure_monitor_set,
    list_procedure_monitor_sets,
    register_procedure_monitor_event,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["procedure-monitor"])


def _to_record_response(result: tuple) -> ProcedureMonitorRecordResponse:
    record, events, alerts = result
    return ProcedureMonitorRecordResponse(
        procedure_monitor_id=record.procedure_monitor_id,
        procedure_monitor_set_id=record.procedure_monitor_set_id,
        current_stage=record.current_stage,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=[ProcedureMonitorEventResponse.model_validate(item) for item in events],
        alerts=[ProcedureMonitorAlertResponse.model_validate(item) for item in alerts],
    )


def _to_set_response(result: tuple) -> ProcedureMonitorSetResponse:
    monitor_set, records = result
    return ProcedureMonitorSetResponse(
        procedure_monitor_set_id=monitor_set.procedure_monitor_set_id,
        deal_id=monitor_set.deal_id,
        procedure_status=monitor_set.procedure_status,
        created_at=monitor_set.created_at,
        updated_at=monitor_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/procedure-monitor/build", response_model=ProcedureMonitorSetResponse, status_code=status.HTTP_201_CREATED)
def build_procedure_monitor_route(
    payload: BuildProcedureMonitorRequest,
    session: DBSession,
) -> ProcedureMonitorSetResponse:
    monitor_set = build_procedure_monitor(session, payload)
    return _to_set_response(get_procedure_monitor_set(session, monitor_set.procedure_monitor_set_id))


@router.post("/procedure-monitor/events", response_model=ProcedureMonitorEventResponse, status_code=status.HTTP_201_CREATED)
def register_procedure_monitor_event_route(
    payload: RegisterProcedureMonitorEventRequest,
    session: DBSession,
) -> ProcedureMonitorEventResponse:
    event = register_procedure_monitor_event(session, payload)
    return ProcedureMonitorEventResponse.model_validate(event)


@router.get("/procedure-monitor/{procedure_monitor_set_id}", response_model=ProcedureMonitorSetResponse)
def get_procedure_monitor_set_route(
    procedure_monitor_set_id: str,
    session: DBSession,
) -> ProcedureMonitorSetResponse:
    return _to_set_response(get_procedure_monitor_set(session, procedure_monitor_set_id))


@router.get("/procedure-monitor", response_model=list[ProcedureMonitorSetResponse])
def list_procedure_monitor_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[ProcedureMonitorSetResponse]:
    return [_to_set_response(item) for item in list_procedure_monitor_sets(session, deal_id=deal_id)]


@router.get("/procedure-monitor/records/{procedure_monitor_id}", response_model=ProcedureMonitorRecordResponse)
def get_procedure_monitor_record_route(
    procedure_monitor_id: str,
    session: DBSession,
) -> ProcedureMonitorRecordResponse:
    return _to_record_response(get_procedure_monitor_record(session, procedure_monitor_id))
