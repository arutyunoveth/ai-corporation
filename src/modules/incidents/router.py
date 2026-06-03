from fastapi import APIRouter, Query, status

from src.modules.incidents.schemas import (
    BuildIncidentSetRequest,
    EscalateIncidentRequest,
    EscalationRecordResponse,
    IncidentRecordResponse,
    IncidentSetResponse,
    RegisterIncidentRequest,
)
from src.modules.incidents.service import (
    build_incident_set,
    escalate_incident,
    get_incident_record,
    get_incident_set,
    list_incident_sets,
    register_incident,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["incidents"])


def _to_escalation_response(item) -> EscalationRecordResponse:
    return EscalationRecordResponse.model_validate(item)


def _to_record_response(result: tuple) -> IncidentRecordResponse:
    record, escalations = result
    return IncidentRecordResponse(
        incident_id=record.incident_id,
        incident_set_id=record.incident_set_id,
        incident_type=record.incident_type,
        severity=record.severity,
        summary=record.summary,
        source_ref=record.source_ref,
        created_at=record.created_at,
        updated_at=record.updated_at,
        escalations=[_to_escalation_response(item) for item in escalations],
    )


def _to_set_response(result: tuple) -> IncidentSetResponse:
    incident_set, records = result
    return IncidentSetResponse(
        incident_set_id=incident_set.incident_set_id,
        deal_id=incident_set.deal_id,
        execution_command_set_id=incident_set.execution_command_set_id,
        incident_status=incident_set.incident_status,
        created_at=incident_set.created_at,
        updated_at=incident_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/incidents/build", response_model=IncidentSetResponse, status_code=status.HTTP_201_CREATED)
def build_incident_set_route(payload: BuildIncidentSetRequest, session: DBSession) -> IncidentSetResponse:
    incident_set = build_incident_set(session, payload)
    return _to_set_response(get_incident_set(session, incident_set.incident_set_id))


@router.post("/incidents/register", response_model=IncidentRecordResponse, status_code=status.HTTP_201_CREATED)
def register_incident_route(payload: RegisterIncidentRequest, session: DBSession) -> IncidentRecordResponse:
    record = register_incident(session, payload)
    return _to_record_response(get_incident_record(session, record.incident_id))


@router.post("/incidents/escalate", response_model=EscalationRecordResponse, status_code=status.HTTP_201_CREATED)
def escalate_incident_route(payload: EscalateIncidentRequest, session: DBSession) -> EscalationRecordResponse:
    escalation = escalate_incident(session, payload)
    return _to_escalation_response(escalation)


@router.get("/incidents/{incident_set_id}", response_model=IncidentSetResponse)
def get_incident_set_route(incident_set_id: str, session: DBSession) -> IncidentSetResponse:
    return _to_set_response(get_incident_set(session, incident_set_id))


@router.get("/incidents", response_model=list[IncidentSetResponse])
def list_incident_sets_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[IncidentSetResponse]:
    return [_to_set_response(item) for item in list_incident_sets(session, deal_id=deal_id)]


@router.get("/incidents/records/{incident_id}", response_model=IncidentRecordResponse)
def get_incident_record_route(incident_id: str, session: DBSession) -> IncidentRecordResponse:
    return _to_record_response(get_incident_record(session, incident_id))
