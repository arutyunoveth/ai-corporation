from fastapi import APIRouter

from src.modules.status_engine.schemas import (
    ApplyTransitionRequest,
    StatusHistoryEntry,
    ValidateTransitionRequest,
    ValidateTransitionResponse,
)
from src.modules.status_engine.service import apply_transition, get_status_history, validate_transition
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["status"])


@router.post("/status/validate-transition", response_model=ValidateTransitionResponse)
def validate_transition_route(payload: ValidateTransitionRequest, session: DBSession) -> ValidateTransitionResponse:
    allowed, reason = validate_transition(session, payload)
    return ValidateTransitionResponse(allowed=allowed, reason=reason)


@router.post("/status/apply-transition", response_model=StatusHistoryEntry)
def apply_transition_route(payload: ApplyTransitionRequest, session: DBSession) -> StatusHistoryEntry:
    history = apply_transition(session, payload)
    return StatusHistoryEntry.model_validate(history)


@router.get("/status/history/{deal_id}", response_model=list[StatusHistoryEntry])
def get_status_history_route(deal_id: str, session: DBSession) -> list[StatusHistoryEntry]:
    return [StatusHistoryEntry.model_validate(entry) for entry in get_status_history(session, deal_id)]

