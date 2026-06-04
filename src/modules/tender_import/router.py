from fastapi import APIRouter, status

from src.modules.tender_import.schemas import (
    CreateTenderImportRunRequest,
    TenderImportEventResponse,
    TenderImportPayloadResponse,
    TenderImportRunResponse,
)
from src.modules.tender_import.service import (
    create_tender_import_run,
    get_tender_import_event,
    get_tender_import_run,
    list_tender_import_events,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["tender-import"])


def _to_payload_response(payload) -> TenderImportPayloadResponse:
    return TenderImportPayloadResponse.model_validate(payload)


def _to_event_response(result: tuple) -> TenderImportEventResponse:
    event, payload = result
    return TenderImportEventResponse(
        tender_import_event_id=event.tender_import_event_id,
        tender_import_run_id=event.tender_import_run_id,
        raw_procurement_number=event.raw_procurement_number,
        source_url=event.source_url,
        created_at=event.created_at,
        updated_at=event.updated_at,
        payload=_to_payload_response(payload),
    )


def _to_run_response(result: tuple) -> TenderImportRunResponse:
    run, events = result
    return TenderImportRunResponse(
        tender_import_run_id=run.tender_import_run_id,
        source_type=run.source_type,
        source_ref=run.source_ref,
        run_status=run.run_status,
        created_at=run.created_at,
        updated_at=run.updated_at,
        events=[_to_event_response(item) for item in events],
    )


@router.post("/tender-import/runs", response_model=TenderImportRunResponse, status_code=status.HTTP_201_CREATED)
def create_tender_import_run_route(
    payload: CreateTenderImportRunRequest,
    session: DBSession,
) -> TenderImportRunResponse:
    run = create_tender_import_run(session, payload)
    return _to_run_response(get_tender_import_run(session, run.tender_import_run_id))


@router.get("/tender-import/runs/{tender_import_run_id}", response_model=TenderImportRunResponse)
def get_tender_import_run_route(tender_import_run_id: str, session: DBSession) -> TenderImportRunResponse:
    return _to_run_response(get_tender_import_run(session, tender_import_run_id))


@router.get("/tender-import/events", response_model=list[TenderImportEventResponse])
def list_tender_import_events_route(session: DBSession) -> list[TenderImportEventResponse]:
    return [_to_event_response(item) for item in list_tender_import_events(session)]


@router.get("/tender-import/events/{tender_import_event_id}", response_model=TenderImportEventResponse)
def get_tender_import_event_route(tender_import_event_id: str, session: DBSession) -> TenderImportEventResponse:
    return _to_event_response(get_tender_import_event(session, tender_import_event_id))
