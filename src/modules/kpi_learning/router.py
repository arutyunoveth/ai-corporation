from fastapi import APIRouter, Query, status

from src.modules.kpi_learning.schemas import (
    BuildKPILearningRequest,
    KPILearningRecordResponse,
    KPILearningSetResponse,
    LearningNoteRecordResponse,
)
from src.modules.kpi_learning.service import (
    build_kpi_learning,
    get_kpi_learning_record,
    get_kpi_learning_set,
    list_kpi_learning_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["kpi-learning"])


def _to_note_response(item) -> LearningNoteRecordResponse:
    return LearningNoteRecordResponse.model_validate(item)


def _to_record_response(result: tuple) -> KPILearningRecordResponse:
    record, notes = result
    return KPILearningRecordResponse(
        kpi_learning_id=record.kpi_learning_id,
        kpi_learning_set_id=record.kpi_learning_set_id,
        cycle_time_days=record.cycle_time_days,
        margin_estimate=record.margin_estimate,
        supplier_count=record.supplier_count,
        incident_count=record.incident_count,
        payment_collection_days=record.payment_collection_days,
        created_at=record.created_at,
        updated_at=record.updated_at,
        learning_notes=[_to_note_response(item) for item in notes],
    )


def _to_set_response(result: tuple) -> KPILearningSetResponse:
    kpi_set, records = result
    return KPILearningSetResponse(
        kpi_learning_set_id=kpi_set.kpi_learning_set_id,
        deal_id=kpi_set.deal_id,
        deal_closure_set_id=kpi_set.deal_closure_set_id,
        kpi_status=kpi_set.kpi_status,
        created_at=kpi_set.created_at,
        updated_at=kpi_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/kpi-learning/build", response_model=KPILearningSetResponse, status_code=status.HTTP_201_CREATED)
def build_kpi_learning_route(payload: BuildKPILearningRequest, session: DBSession) -> KPILearningSetResponse:
    kpi_set = build_kpi_learning(session, payload)
    return _to_set_response(get_kpi_learning_set(session, kpi_set.kpi_learning_set_id))


@router.get("/kpi-learning/{kpi_learning_set_id}", response_model=KPILearningSetResponse)
def get_kpi_learning_set_route(kpi_learning_set_id: str, session: DBSession) -> KPILearningSetResponse:
    return _to_set_response(get_kpi_learning_set(session, kpi_learning_set_id))


@router.get("/kpi-learning", response_model=list[KPILearningSetResponse])
def list_kpi_learning_sets_route(
    session: DBSession, deal_id: str | None = Query(default=None)
) -> list[KPILearningSetResponse]:
    return [_to_set_response(item) for item in list_kpi_learning_sets(session, deal_id=deal_id)]


@router.get("/kpi-learning/records/{kpi_learning_id}", response_model=KPILearningRecordResponse)
def get_kpi_learning_record_route(kpi_learning_id: str, session: DBSession) -> KPILearningRecordResponse:
    return _to_record_response(get_kpi_learning_record(session, kpi_learning_id))
