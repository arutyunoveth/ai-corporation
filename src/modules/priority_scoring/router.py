from fastapi import APIRouter, Query, status

from src.modules.priority_scoring.schemas import PriorityScoreResponse, RunPriorityScoringRequest
from src.modules.priority_scoring.service import get_priority_score, list_priority_scores, run_priority_scoring
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["priority-scoring"])


@router.post("/priority-scoring/run", response_model=PriorityScoreResponse, status_code=status.HTTP_201_CREATED)
def run_priority_scoring_route(payload: RunPriorityScoringRequest, session: DBSession) -> PriorityScoreResponse:
    return PriorityScoreResponse.model_validate(run_priority_scoring(session, payload))


@router.get("/priority-scoring/{priority_score_id}", response_model=PriorityScoreResponse)
def get_priority_score_route(priority_score_id: str, session: DBSession) -> PriorityScoreResponse:
    return PriorityScoreResponse.model_validate(get_priority_score(session, priority_score_id))


@router.get("/priority-scoring", response_model=list[PriorityScoreResponse])
def list_priority_scores_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[PriorityScoreResponse]:
    return [PriorityScoreResponse.model_validate(item) for item in list_priority_scores(session, deal_id=deal_id)]

