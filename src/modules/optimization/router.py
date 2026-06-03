from fastapi import APIRouter, Query, status

from src.modules.optimization.schemas import (
    BuildOptimizationRequest,
    OptimizationRecommendationRecordResponse,
    OptimizationRecommendationSetResponse,
    OptimizationSignalRecordResponse,
)
from src.modules.optimization.service import (
    build_optimization,
    get_optimization_record,
    get_optimization_set,
    list_optimization_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import OptimizationScopeType

router = APIRouter(tags=["optimization"])


def _to_signal_response(item) -> OptimizationSignalRecordResponse:
    return OptimizationSignalRecordResponse.model_validate(item)


def _to_record_response(result: tuple) -> OptimizationRecommendationRecordResponse:
    record, signals = result
    return OptimizationRecommendationRecordResponse(
        optimization_recommendation_id=record.optimization_recommendation_id,
        optimization_recommendation_set_id=record.optimization_recommendation_set_id,
        recommendation_code=record.recommendation_code,
        recommendation_type=record.recommendation_type,
        recommendation_text=record.recommendation_text,
        confidence_score=record.confidence_score,
        created_at=record.created_at,
        updated_at=record.updated_at,
        signals=[_to_signal_response(item) for item in signals],
    )


def _to_set_response(result: tuple) -> OptimizationRecommendationSetResponse:
    optimization_set, records = result
    return OptimizationRecommendationSetResponse(
        optimization_recommendation_set_id=optimization_set.optimization_recommendation_set_id,
        scope_type=optimization_set.scope_type,
        scope_ref=optimization_set.scope_ref,
        optimization_status=optimization_set.optimization_status,
        created_at=optimization_set.created_at,
        updated_at=optimization_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/optimization/build", response_model=OptimizationRecommendationSetResponse, status_code=status.HTTP_201_CREATED)
def build_optimization_route(payload: BuildOptimizationRequest, session: DBSession) -> OptimizationRecommendationSetResponse:
    optimization_set = build_optimization(session, payload)
    return _to_set_response(get_optimization_set(session, optimization_set.optimization_recommendation_set_id))


@router.get("/optimization/{optimization_recommendation_set_id}", response_model=OptimizationRecommendationSetResponse)
def get_optimization_set_route(
    optimization_recommendation_set_id: str, session: DBSession
) -> OptimizationRecommendationSetResponse:
    return _to_set_response(get_optimization_set(session, optimization_recommendation_set_id))


@router.get("/optimization", response_model=list[OptimizationRecommendationSetResponse])
def list_optimization_sets_route(
    session: DBSession,
    scope_type: OptimizationScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[OptimizationRecommendationSetResponse]:
    return [_to_set_response(item) for item in list_optimization_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/optimization/records/{optimization_recommendation_id}", response_model=OptimizationRecommendationRecordResponse)
def get_optimization_record_route(
    optimization_recommendation_id: str, session: DBSession
) -> OptimizationRecommendationRecordResponse:
    return _to_record_response(get_optimization_record(session, optimization_recommendation_id))
