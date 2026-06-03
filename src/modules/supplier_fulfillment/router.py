from fastapi import APIRouter, Query, status

from src.modules.supplier_fulfillment.schemas import (
    BuildSupplierFulfillmentRequest,
    RegisterSupplierFulfillmentEventRequest,
    SupplierFulfillmentEventResponse,
    SupplierFulfillmentRecordResponse,
    SupplierFulfillmentSetResponse,
)
from src.modules.supplier_fulfillment.service import (
    build_supplier_fulfillment,
    get_supplier_fulfillment_record,
    get_supplier_fulfillment_set,
    list_supplier_fulfillment_sets,
    register_supplier_fulfillment_event,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["supplier-fulfillment"])


def _to_event_response(item) -> SupplierFulfillmentEventResponse:
    return SupplierFulfillmentEventResponse.model_validate(item)


def _to_record_response(result: tuple) -> SupplierFulfillmentRecordResponse:
    record, events = result
    return SupplierFulfillmentRecordResponse(
        supplier_fulfillment_id=record.supplier_fulfillment_id,
        supplier_fulfillment_set_id=record.supplier_fulfillment_set_id,
        supplier_id=record.supplier_id,
        fulfillment_state=record.fulfillment_state,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=[_to_event_response(item) for item in events],
    )


def _to_set_response(result: tuple) -> SupplierFulfillmentSetResponse:
    fulfillment_set, records = result
    return SupplierFulfillmentSetResponse(
        supplier_fulfillment_set_id=fulfillment_set.supplier_fulfillment_set_id,
        deal_id=fulfillment_set.deal_id,
        execution_command_set_id=fulfillment_set.execution_command_set_id,
        fulfillment_status=fulfillment_set.fulfillment_status,
        created_at=fulfillment_set.created_at,
        updated_at=fulfillment_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/supplier-fulfillment/build", response_model=SupplierFulfillmentSetResponse, status_code=status.HTTP_201_CREATED)
def build_supplier_fulfillment_route(
    payload: BuildSupplierFulfillmentRequest,
    session: DBSession,
) -> SupplierFulfillmentSetResponse:
    fulfillment_set = build_supplier_fulfillment(session, payload)
    return _to_set_response(get_supplier_fulfillment_set(session, fulfillment_set.supplier_fulfillment_set_id))


@router.post("/supplier-fulfillment/events", response_model=SupplierFulfillmentEventResponse, status_code=status.HTTP_201_CREATED)
def register_supplier_fulfillment_event_route(
    payload: RegisterSupplierFulfillmentEventRequest,
    session: DBSession,
) -> SupplierFulfillmentEventResponse:
    return _to_event_response(register_supplier_fulfillment_event(session, payload))


@router.get("/supplier-fulfillment/{supplier_fulfillment_set_id}", response_model=SupplierFulfillmentSetResponse)
def get_supplier_fulfillment_set_route(
    supplier_fulfillment_set_id: str,
    session: DBSession,
) -> SupplierFulfillmentSetResponse:
    return _to_set_response(get_supplier_fulfillment_set(session, supplier_fulfillment_set_id))


@router.get("/supplier-fulfillment", response_model=list[SupplierFulfillmentSetResponse])
def list_supplier_fulfillment_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[SupplierFulfillmentSetResponse]:
    return [_to_set_response(item) for item in list_supplier_fulfillment_sets(session, deal_id=deal_id)]


@router.get("/supplier-fulfillment/records/{supplier_fulfillment_id}", response_model=SupplierFulfillmentRecordResponse)
def get_supplier_fulfillment_record_route(
    supplier_fulfillment_id: str,
    session: DBSession,
) -> SupplierFulfillmentRecordResponse:
    return _to_record_response(get_supplier_fulfillment_record(session, supplier_fulfillment_id))
