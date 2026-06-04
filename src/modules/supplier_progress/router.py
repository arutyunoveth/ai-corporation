from fastapi import APIRouter, Query, status

from src.modules.supplier_progress.schemas import (
    BuildSupplierProgressRequest,
    RegisterSupplierProgressEventRequest,
    SupplierProgressAlertResponse,
    SupplierProgressEventResponse,
    SupplierProgressRecordResponse,
    SupplierProgressSetResponse,
)
from src.modules.supplier_progress.service import (
    build_supplier_progress,
    get_supplier_progress_record,
    get_supplier_progress_set,
    list_supplier_progress_sets,
    register_supplier_progress_event,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["supplier-progress"])


def _to_record_response(result: tuple) -> SupplierProgressRecordResponse:
    record, events, alerts = result
    return SupplierProgressRecordResponse(
        supplier_progress_id=record.supplier_progress_id,
        readiness_state=record.readiness_state,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=[SupplierProgressEventResponse.model_validate(item) for item in events],
        alerts=[SupplierProgressAlertResponse.model_validate(item) for item in alerts],
    )


def _to_set_response(result: tuple) -> SupplierProgressSetResponse:
    progress_set, records = result
    return SupplierProgressSetResponse(
        supplier_progress_set_id=progress_set.supplier_progress_set_id,
        deal_id=progress_set.deal_id,
        supplier_id=progress_set.supplier_id,
        progress_status=progress_set.progress_status,
        created_at=progress_set.created_at,
        updated_at=progress_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/supplier-progress/build", response_model=SupplierProgressSetResponse, status_code=status.HTTP_201_CREATED)
def build_supplier_progress_route(payload: BuildSupplierProgressRequest, session: DBSession) -> SupplierProgressSetResponse:
    progress_set = build_supplier_progress(session, payload)
    return _to_set_response(get_supplier_progress_set(session, progress_set.supplier_progress_set_id))


@router.post("/supplier-progress/events", response_model=SupplierProgressEventResponse, status_code=status.HTTP_201_CREATED)
def register_supplier_progress_event_route(
    payload: RegisterSupplierProgressEventRequest,
    session: DBSession,
) -> SupplierProgressEventResponse:
    return SupplierProgressEventResponse.model_validate(register_supplier_progress_event(session, payload))


@router.get("/supplier-progress/{supplier_progress_set_id}", response_model=SupplierProgressSetResponse)
def get_supplier_progress_set_route(supplier_progress_set_id: str, session: DBSession) -> SupplierProgressSetResponse:
    return _to_set_response(get_supplier_progress_set(session, supplier_progress_set_id))


@router.get("/supplier-progress", response_model=list[SupplierProgressSetResponse])
def list_supplier_progress_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[SupplierProgressSetResponse]:
    return [_to_set_response(item) for item in list_supplier_progress_sets(session, deal_id=deal_id)]


@router.get("/supplier-progress/records/{supplier_progress_id}", response_model=SupplierProgressRecordResponse)
def get_supplier_progress_record_route(supplier_progress_id: str, session: DBSession) -> SupplierProgressRecordResponse:
    return _to_record_response(get_supplier_progress_record(session, supplier_progress_id))
