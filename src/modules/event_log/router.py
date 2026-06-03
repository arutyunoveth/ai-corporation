from fastapi import APIRouter, Query, status

from src.modules.event_log.schemas import AppendDecisionRequest, AppendEventRequest, DecisionResponse, EventResponse
from src.modules.event_log.service import append_decision, append_event, list_decisions, list_events
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["events"])


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def append_event_route(payload: AppendEventRequest, session: DBSession) -> EventResponse:
    return EventResponse.model_validate(append_event(session, payload))


@router.post("/decisions", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
def append_decision_route(payload: AppendDecisionRequest, session: DBSession) -> DecisionResponse:
    return DecisionResponse.model_validate(append_decision(session, payload))


@router.get("/events", response_model=list[EventResponse])
def list_events_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[EventResponse]:
    return [EventResponse.model_validate(item) for item in list_events(session, deal_id=deal_id)]


@router.get("/decisions", response_model=list[DecisionResponse])
def list_decisions_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[DecisionResponse]:
    return [DecisionResponse.model_validate(item) for item in list_decisions(session, deal_id=deal_id)]
