from fastapi import APIRouter, status

from src.modules.tender_normalization.schemas import (
    BuildTenderNormalizationRequest,
    TenderNormalizationLinkResponse,
    TenderNormalizationRecordResponse,
    TenderNormalizationSetResponse,
)
from src.modules.tender_normalization.service import (
    build_tender_normalization,
    get_tender_normalization_record,
    get_tender_normalization_set,
    list_tender_normalization_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["tender-normalization"])


def _to_link_response(item) -> TenderNormalizationLinkResponse:
    return TenderNormalizationLinkResponse.model_validate(item)


def _to_record_response(result: tuple) -> TenderNormalizationRecordResponse:
    record, links = result
    return TenderNormalizationRecordResponse(
        tender_normalization_id=record.tender_normalization_id,
        tender_normalization_set_id=record.tender_normalization_set_id,
        normalized_procurement_number=record.normalized_procurement_number,
        normalized_title=record.normalized_title,
        normalized_customer_name=record.normalized_customer_name,
        normalized_deadline_at=record.normalized_deadline_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        links=[_to_link_response(item) for item in links],
    )


def _to_set_response(result: tuple) -> TenderNormalizationSetResponse:
    normalization_set, records = result
    return TenderNormalizationSetResponse(
        tender_normalization_set_id=normalization_set.tender_normalization_set_id,
        tender_import_event_id=normalization_set.tender_import_event_id,
        normalization_status=normalization_set.normalization_status,
        created_at=normalization_set.created_at,
        updated_at=normalization_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/tender-normalization/build", response_model=TenderNormalizationSetResponse, status_code=status.HTTP_201_CREATED)
def build_tender_normalization_route(
    payload: BuildTenderNormalizationRequest,
    session: DBSession,
) -> TenderNormalizationSetResponse:
    normalization_set = build_tender_normalization(session, payload.tender_import_event_id)
    return _to_set_response(get_tender_normalization_set(session, normalization_set.tender_normalization_set_id))


@router.get("/tender-normalization/{tender_normalization_set_id}", response_model=TenderNormalizationSetResponse)
def get_tender_normalization_set_route(
    tender_normalization_set_id: str,
    session: DBSession,
) -> TenderNormalizationSetResponse:
    return _to_set_response(get_tender_normalization_set(session, tender_normalization_set_id))


@router.get("/tender-normalization", response_model=list[TenderNormalizationSetResponse])
def list_tender_normalization_sets_route(session: DBSession) -> list[TenderNormalizationSetResponse]:
    return [_to_set_response(item) for item in list_tender_normalization_sets(session)]


@router.get("/tender-normalization/records/{tender_normalization_id}", response_model=TenderNormalizationRecordResponse)
def get_tender_normalization_record_route(
    tender_normalization_id: str,
    session: DBSession,
) -> TenderNormalizationRecordResponse:
    return _to_record_response(get_tender_normalization_record(session, tender_normalization_id))
