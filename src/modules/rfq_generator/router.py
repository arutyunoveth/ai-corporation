from fastapi import APIRouter, Query, status

from src.modules.rfq_generator.schemas import BuildRFQBatchRequest, RFQBatchResponse, RFQRecordResponse
from src.modules.rfq_generator.service import build_rfq_batch, get_rfq_batch, get_rfq_record, list_rfq_batches
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["rfq"])


def _to_rfq_record_response(result: tuple) -> RFQRecordResponse:
    record, artifact_refs = result
    return RFQRecordResponse(
        rfq_id=record.rfq_id,
        rfq_batch_id=record.rfq_batch_id,
        supplier_id=record.supplier_id,
        subject=record.subject,
        body_text=record.body_text,
        rfq_status=record.rfq_status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        artifact_refs=artifact_refs,
    )


def _to_rfq_batch_response(result: tuple) -> RFQBatchResponse:
    batch, records = result
    return RFQBatchResponse(
        rfq_batch_id=batch.rfq_batch_id,
        deal_id=batch.deal_id,
        supplier_shortlist_id=batch.supplier_shortlist_id,
        batch_status=batch.batch_status,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        rfq_records=[_to_rfq_record_response(item) for item in records],
    )


@router.post("/rfq/batches/build", response_model=RFQBatchResponse, status_code=status.HTTP_201_CREATED)
def build_rfq_batch_route(payload: BuildRFQBatchRequest, session: DBSession) -> RFQBatchResponse:
    batch = build_rfq_batch(session, payload)
    return _to_rfq_batch_response(get_rfq_batch(session, batch.rfq_batch_id))


@router.get("/rfq/batches/{rfq_batch_id}", response_model=RFQBatchResponse)
def get_rfq_batch_route(rfq_batch_id: str, session: DBSession) -> RFQBatchResponse:
    return _to_rfq_batch_response(get_rfq_batch(session, rfq_batch_id))


@router.get("/rfq/batches", response_model=list[RFQBatchResponse])
def list_rfq_batches_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[RFQBatchResponse]:
    return [_to_rfq_batch_response(item) for item in list_rfq_batches(session, deal_id=deal_id)]


@router.get("/rfq/records/{rfq_id}", response_model=RFQRecordResponse)
def get_rfq_record_route(rfq_id: str, session: DBSession) -> RFQRecordResponse:
    return _to_rfq_record_response(get_rfq_record(session, rfq_id))
