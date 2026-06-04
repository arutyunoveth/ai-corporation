from fastapi import APIRouter, Query, status

from src.modules.incident_register.schemas import (
    BuildIncidentRegisterRequest,
    IncidentRegisterEventResponse,
    IncidentRegisterFlagResponse,
    IncidentRegisterRecordResponse,
    IncidentRegisterSetResponse,
    RegisterIncidentRegisterEventRequest,
)
from src.modules.incident_register.service import (
    build_incident_register,
    get_incident_register_record,
    get_incident_register_set,
    list_incident_register_sets,
    register_incident_register_event,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["incident-register"])


def _to_record_response(result: tuple) -> IncidentRegisterRecordResponse:
    record, events, flags = result
    return IncidentRegisterRecordResponse(
        incident_register_id=record.incident_register_id,
        incident_type=record.incident_type,
        severity=record.severity,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=[IncidentRegisterEventResponse.model_validate(item) for item in events],
        flags=[IncidentRegisterFlagResponse.model_validate(item) for item in flags],
    )


def _to_set_response(result: tuple) -> IncidentRegisterSetResponse:
    register_set, records = result
    return IncidentRegisterSetResponse(
        incident_register_set_id=register_set.incident_register_set_id,
        deal_id=register_set.deal_id,
        incident_status=register_set.incident_status,
        created_at=register_set.created_at,
        updated_at=register_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/incident-register/build", response_model=IncidentRegisterSetResponse, status_code=status.HTTP_201_CREATED)
def build_incident_register_route(payload: BuildIncidentRegisterRequest, session: DBSession) -> IncidentRegisterSetResponse:
    register_set = build_incident_register(session, payload)
    return _to_set_response(get_incident_register_set(session, register_set.incident_register_set_id))


@router.post("/incident-register/events", response_model=IncidentRegisterEventResponse, status_code=status.HTTP_201_CREATED)
def register_incident_register_event_route(
    payload: RegisterIncidentRegisterEventRequest,
    session: DBSession,
) -> IncidentRegisterEventResponse:
    event = register_incident_register_event(session, payload)
    return IncidentRegisterEventResponse.model_validate(event)


@router.get("/incident-register/{incident_register_set_id}", response_model=IncidentRegisterSetResponse)
def get_incident_register_set_route(incident_register_set_id: str, session: DBSession) -> IncidentRegisterSetResponse:
    return _to_set_response(get_incident_register_set(session, incident_register_set_id))


@router.get("/incident-register", response_model=list[IncidentRegisterSetResponse])
def list_incident_register_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[IncidentRegisterSetResponse]:
    return [_to_set_response(item) for item in list_incident_register_sets(session, deal_id=deal_id)]


@router.get("/incident-register/records/{incident_register_id}", response_model=IncidentRegisterRecordResponse)
def get_incident_register_record_route(incident_register_id: str, session: DBSession) -> IncidentRegisterRecordResponse:
    return _to_record_response(get_incident_register_record(session, incident_register_id))
