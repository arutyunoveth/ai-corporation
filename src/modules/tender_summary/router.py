from fastapi import APIRouter, Query, status

from src.modules.tender_summary.schemas import (
    BuildTenderSummaryRequest,
    BuildTenderSummaryResponse,
    TenderSummaryResponse,
    TenderSummarySourceLinkResponse,
)
from src.modules.tender_summary.service import build_tender_summary, get_tender_summary, list_tender_summaries
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["tender-summary"])


def _to_response(summary_and_links: tuple) -> TenderSummaryResponse:
    summary, source_links = summary_and_links
    return TenderSummaryResponse(
        tender_summary_id=summary.tender_summary_id,
        deal_id=summary.deal_id,
        intake_id=summary.intake_id,
        document_set_id=summary.document_set_id,
        summary_status=summary.summary_status,
        summary_text=summary.summary_text,
        structured_summary_json=summary.structured_summary_json,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
        source_links=[TenderSummarySourceLinkResponse.model_validate(link) for link in source_links],
    )


@router.post("/tender-summaries", response_model=BuildTenderSummaryResponse, status_code=status.HTTP_201_CREATED)
def build_tender_summary_route(payload: BuildTenderSummaryRequest, session: DBSession) -> BuildTenderSummaryResponse:
    summary = build_tender_summary(session, payload)
    return BuildTenderSummaryResponse(tender_summary_id=summary.tender_summary_id, summary_status=summary.summary_status)


@router.get("/tender-summaries/{tender_summary_id}", response_model=TenderSummaryResponse)
def get_tender_summary_route(tender_summary_id: str, session: DBSession) -> TenderSummaryResponse:
    return _to_response(get_tender_summary(session, tender_summary_id))


@router.get("/tender-summaries", response_model=list[TenderSummaryResponse])
def list_tender_summaries_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[TenderSummaryResponse]:
    return [_to_response(item) for item in list_tender_summaries(session, deal_id=deal_id)]
