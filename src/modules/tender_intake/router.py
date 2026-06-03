from fastapi import APIRouter, Query, status

from src.modules.tender_intake.schemas import CreateTenderIntakeRequest, CreateTenderIntakeResponse, TenderIntakeResponse
from src.modules.tender_intake.service import create_tender_intake, get_tender_intake, list_tender_intakes
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["tender-intake"])


def _to_response(record_and_payload: tuple) -> TenderIntakeResponse:
    record, payload = record_and_payload
    return TenderIntakeResponse(
        intake_id=record.intake_id,
        deal_id=record.deal_id,
        source_type=record.source_type,
        source_channel=record.source_channel,
        source_title=record.source_title,
        source_customer_name=record.source_customer_name,
        source_procurement_number=record.source_procurement_number,
        intake_status=record.intake_status,
        duplicate_hint=record.duplicate_hint,
        payload_json=payload.payload_json,
        payload_hash=payload.payload_hash,
        received_at=record.received_at,
        normalized_at=record.normalized_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/intake/tenders", response_model=CreateTenderIntakeResponse, status_code=status.HTTP_201_CREATED)
def create_tender_intake_route(payload: CreateTenderIntakeRequest, session: DBSession) -> CreateTenderIntakeResponse:
    intake, _ = create_tender_intake(session, payload)
    return CreateTenderIntakeResponse(
        intake_id=intake.intake_id,
        deal_id=intake.deal_id,
        intake_status=intake.intake_status,
        duplicate_hint=intake.duplicate_hint,
    )


@router.get("/intake/tenders/{intake_id}", response_model=TenderIntakeResponse)
def get_tender_intake_route(intake_id: str, session: DBSession) -> TenderIntakeResponse:
    return _to_response(get_tender_intake(session, intake_id))


@router.get("/intake/tenders", response_model=list[TenderIntakeResponse])
def list_tender_intakes_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[TenderIntakeResponse]:
    return [_to_response(item) for item in list_tender_intakes(session, deal_id=deal_id)]

