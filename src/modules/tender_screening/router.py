from fastapi import APIRouter, Query, status

from src.modules.tender_screening.schemas import RunScreeningRequest, TenderScreeningResponse
from src.modules.tender_screening.service import get_screening, list_screenings, run_screening
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["screening"])


@router.post("/screening/run", response_model=TenderScreeningResponse, status_code=status.HTTP_201_CREATED)
def run_screening_route(payload: RunScreeningRequest, session: DBSession) -> TenderScreeningResponse:
    return TenderScreeningResponse.model_validate(run_screening(session, payload))


@router.get("/screening/{screening_id}", response_model=TenderScreeningResponse)
def get_screening_route(screening_id: str, session: DBSession) -> TenderScreeningResponse:
    return TenderScreeningResponse.model_validate(get_screening(session, screening_id))


@router.get("/screening", response_model=list[TenderScreeningResponse])
def list_screenings_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[TenderScreeningResponse]:
    return [TenderScreeningResponse.model_validate(item) for item in list_screenings(session, deal_id=deal_id)]

