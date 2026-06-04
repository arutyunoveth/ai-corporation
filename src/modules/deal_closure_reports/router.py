from fastapi import APIRouter, Query, status

from src.modules.deal_closure_reports.schemas import (
    BuildDealClosureReportRequest,
    DealClosureReportLinkResponse,
    DealClosureReportRecordResponse,
    DealClosureReportSetResponse,
)
from src.modules.deal_closure_reports.service import (
    build_deal_closure_report,
    get_deal_closure_report_record,
    get_deal_closure_report_set,
    list_deal_closure_report_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["deal-closure-reports"])


def _to_record_response(result: tuple) -> DealClosureReportRecordResponse:
    record, links = result
    return DealClosureReportRecordResponse(
        deal_closure_report_id=record.deal_closure_report_id,
        report_code=record.report_code,
        summary_text=record.summary_text,
        closure_health=record.closure_health,
        created_at=record.created_at,
        updated_at=record.updated_at,
        links=[DealClosureReportLinkResponse.model_validate(item) for item in links],
    )


def _to_set_response(result: tuple) -> DealClosureReportSetResponse:
    report_set, records = result
    return DealClosureReportSetResponse(
        deal_closure_report_set_id=report_set.deal_closure_report_set_id,
        deal_id=report_set.deal_id,
        deal_closure_set_id=report_set.deal_closure_set_id,
        acceptance_control_set_id=report_set.acceptance_control_set_id,
        closing_docs_set_id=report_set.closing_docs_set_id,
        payment_tracking_set_id=report_set.payment_tracking_set_id,
        claim_trigger_set_id=report_set.claim_trigger_set_id,
        report_status=report_set.report_status,
        created_at=report_set.created_at,
        updated_at=report_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/deal-closure-reports/build", response_model=DealClosureReportSetResponse, status_code=status.HTTP_201_CREATED)
def build_deal_closure_report_route(
    payload: BuildDealClosureReportRequest,
    session: DBSession,
) -> DealClosureReportSetResponse:
    report_set = build_deal_closure_report(session, payload)
    return _to_set_response(get_deal_closure_report_set(session, report_set.deal_closure_report_set_id))


@router.get("/deal-closure-reports/{deal_closure_report_set_id}", response_model=DealClosureReportSetResponse)
def get_deal_closure_report_set_route(
    deal_closure_report_set_id: str,
    session: DBSession,
) -> DealClosureReportSetResponse:
    return _to_set_response(get_deal_closure_report_set(session, deal_closure_report_set_id))


@router.get("/deal-closure-reports", response_model=list[DealClosureReportSetResponse])
def list_deal_closure_report_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[DealClosureReportSetResponse]:
    return [_to_set_response(item) for item in list_deal_closure_report_sets(session, deal_id=deal_id)]


@router.get("/deal-closure-reports/records/{deal_closure_report_id}", response_model=DealClosureReportRecordResponse)
def get_deal_closure_report_record_route(
    deal_closure_report_id: str,
    session: DBSession,
) -> DealClosureReportRecordResponse:
    return _to_record_response(get_deal_closure_report_record(session, deal_closure_report_id))
