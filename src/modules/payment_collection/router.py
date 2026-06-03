from fastapi import APIRouter, Query, status

from src.modules.payment_collection.schemas import (
    BuildPaymentCollectionRequest,
    PaymentCollectionEventResponse,
    PaymentCollectionRecordResponse,
    PaymentCollectionSetResponse,
    RegisterPaymentCollectionEventRequest,
)
from src.modules.payment_collection.service import (
    build_payment_collection,
    get_payment_collection_record,
    get_payment_collection_set,
    list_payment_collection_sets,
    register_payment_collection_event,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["payment-collection"])


def _to_event_response(item) -> PaymentCollectionEventResponse:
    return PaymentCollectionEventResponse.model_validate(item)


def _to_record_response(result: tuple) -> PaymentCollectionRecordResponse:
    record, events = result
    return PaymentCollectionRecordResponse(
        payment_collection_id=record.payment_collection_id,
        payment_collection_set_id=record.payment_collection_set_id,
        invoice_ref=record.invoice_ref,
        expected_amount=record.expected_amount,
        collected_amount=record.collected_amount,
        currency_code=record.currency_code,
        collection_state=record.collection_state,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=[_to_event_response(item) for item in events],
    )


def _to_set_response(result: tuple) -> PaymentCollectionSetResponse:
    collection_set, records = result
    return PaymentCollectionSetResponse(
        payment_collection_set_id=collection_set.payment_collection_set_id,
        deal_id=collection_set.deal_id,
        execution_command_set_id=collection_set.execution_command_set_id,
        collection_status=collection_set.collection_status,
        created_at=collection_set.created_at,
        updated_at=collection_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/payment-collection/build", response_model=PaymentCollectionSetResponse, status_code=status.HTTP_201_CREATED)
def build_payment_collection_route(
    payload: BuildPaymentCollectionRequest,
    session: DBSession,
) -> PaymentCollectionSetResponse:
    collection_set = build_payment_collection(session, payload)
    return _to_set_response(get_payment_collection_set(session, collection_set.payment_collection_set_id))


@router.post("/payment-collection/events", response_model=PaymentCollectionEventResponse, status_code=status.HTTP_201_CREATED)
def register_payment_collection_event_route(
    payload: RegisterPaymentCollectionEventRequest,
    session: DBSession,
) -> PaymentCollectionEventResponse:
    return _to_event_response(register_payment_collection_event(session, payload))


@router.get("/payment-collection/{payment_collection_set_id}", response_model=PaymentCollectionSetResponse)
def get_payment_collection_set_route(
    payment_collection_set_id: str,
    session: DBSession,
) -> PaymentCollectionSetResponse:
    return _to_set_response(get_payment_collection_set(session, payment_collection_set_id))


@router.get("/payment-collection", response_model=list[PaymentCollectionSetResponse])
def list_payment_collection_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[PaymentCollectionSetResponse]:
    return [_to_set_response(item) for item in list_payment_collection_sets(session, deal_id=deal_id)]


@router.get("/payment-collection/records/{payment_collection_id}", response_model=PaymentCollectionRecordResponse)
def get_payment_collection_record_route(
    payment_collection_id: str,
    session: DBSession,
) -> PaymentCollectionRecordResponse:
    return _to_record_response(get_payment_collection_record(session, payment_collection_id))
