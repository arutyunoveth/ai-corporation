from fastapi import APIRouter, Query, status

from src.modules.supplier_communications.schemas import (
    BuildSupplierCommunicationSetRequest,
    RecordSupplierMessageRequest,
    SupplierCommunicationSetResponse,
    SupplierCommunicationThreadResponse,
    SupplierMessageRecordResponse,
)
from src.modules.supplier_communications.service import (
    build_supplier_communication_set,
    get_supplier_communication_set,
    get_supplier_thread,
    list_supplier_communication_sets,
    record_supplier_message,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["supplier-communications"])


def _to_thread_response(result: tuple) -> SupplierCommunicationThreadResponse:
    thread, messages = result
    return SupplierCommunicationThreadResponse(
        supplier_thread_id=thread.supplier_thread_id,
        supplier_communication_set_id=thread.supplier_communication_set_id,
        supplier_id=thread.supplier_id,
        rfq_id=thread.rfq_id,
        thread_status=thread.thread_status,
        last_message_at=thread.last_message_at,
        created_at=thread.created_at,
        messages=[SupplierMessageRecordResponse.model_validate(item) for item in messages],
    )


def _to_set_response(result: tuple) -> SupplierCommunicationSetResponse:
    communication_set, threads = result
    return SupplierCommunicationSetResponse(
        supplier_communication_set_id=communication_set.supplier_communication_set_id,
        deal_id=communication_set.deal_id,
        rfq_batch_id=communication_set.rfq_batch_id,
        created_at=communication_set.created_at,
        threads=[_to_thread_response(item) for item in threads],
    )


@router.post(
    "/supplier-communications/sets/build",
    response_model=SupplierCommunicationSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def build_supplier_communication_set_route(
    payload: BuildSupplierCommunicationSetRequest,
    session: DBSession,
) -> SupplierCommunicationSetResponse:
    communication_set = build_supplier_communication_set(session, payload)
    return _to_set_response(get_supplier_communication_set(session, communication_set.supplier_communication_set_id))


@router.get("/supplier-communications/sets/{supplier_communication_set_id}", response_model=SupplierCommunicationSetResponse)
def get_supplier_communication_set_route(
    supplier_communication_set_id: str,
    session: DBSession,
) -> SupplierCommunicationSetResponse:
    return _to_set_response(get_supplier_communication_set(session, supplier_communication_set_id))


@router.get("/supplier-communications/sets", response_model=list[SupplierCommunicationSetResponse])
def list_supplier_communication_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[SupplierCommunicationSetResponse]:
    return [_to_set_response(item) for item in list_supplier_communication_sets(session, deal_id=deal_id)]


@router.post(
    "/supplier-communications/threads/{supplier_thread_id}/messages",
    response_model=SupplierMessageRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_supplier_message_route(
    supplier_thread_id: str,
    payload: RecordSupplierMessageRequest,
    session: DBSession,
) -> SupplierMessageRecordResponse:
    return SupplierMessageRecordResponse.model_validate(record_supplier_message(session, supplier_thread_id, payload))


@router.get("/supplier-communications/threads/{supplier_thread_id}", response_model=SupplierCommunicationThreadResponse)
def get_supplier_thread_route(supplier_thread_id: str, session: DBSession) -> SupplierCommunicationThreadResponse:
    return _to_thread_response(get_supplier_thread(session, supplier_thread_id))
