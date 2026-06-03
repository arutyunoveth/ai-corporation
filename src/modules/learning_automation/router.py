from fastapi import APIRouter, Query, status

from src.modules.learning_automation.schemas import (
    BuildLearningAutomationRequest,
    LearningAutomationRecordResponse,
    LearningAutomationSetResponse,
    LearningRecommendationRecordResponse,
)
from src.modules.learning_automation.service import (
    build_learning_automation,
    get_learning_automation_record,
    get_learning_automation_set,
    list_learning_automation_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import LearningAutomationScopeType

router = APIRouter(tags=["learning-automation"])


def _to_recommendation_response(item) -> LearningRecommendationRecordResponse:
    return LearningRecommendationRecordResponse.model_validate(item)


def _to_record_response(result: tuple) -> LearningAutomationRecordResponse:
    record, recommendations = result
    return LearningAutomationRecordResponse(
        learning_automation_id=record.learning_automation_id,
        learning_automation_set_id=record.learning_automation_set_id,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        recommendations=[_to_recommendation_response(item) for item in recommendations],
    )


def _to_set_response(result: tuple) -> LearningAutomationSetResponse:
    automation_set, records = result
    return LearningAutomationSetResponse(
        learning_automation_set_id=automation_set.learning_automation_set_id,
        scope_type=automation_set.scope_type,
        scope_ref=automation_set.scope_ref,
        automation_status=automation_set.automation_status,
        created_at=automation_set.created_at,
        updated_at=automation_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/learning-automation/build", response_model=LearningAutomationSetResponse, status_code=status.HTTP_201_CREATED)
def build_learning_automation_route(payload: BuildLearningAutomationRequest, session: DBSession) -> LearningAutomationSetResponse:
    automation_set = build_learning_automation(session, payload)
    return _to_set_response(get_learning_automation_set(session, automation_set.learning_automation_set_id))


@router.get("/learning-automation/{learning_automation_set_id}", response_model=LearningAutomationSetResponse)
def get_learning_automation_set_route(
    learning_automation_set_id: str, session: DBSession
) -> LearningAutomationSetResponse:
    return _to_set_response(get_learning_automation_set(session, learning_automation_set_id))


@router.get("/learning-automation", response_model=list[LearningAutomationSetResponse])
def list_learning_automation_sets_route(
    session: DBSession,
    scope_type: LearningAutomationScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[LearningAutomationSetResponse]:
    return [_to_set_response(item) for item in list_learning_automation_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/learning-automation/records/{learning_automation_id}", response_model=LearningAutomationRecordResponse)
def get_learning_automation_record_route(
    learning_automation_id: str, session: DBSession
) -> LearningAutomationRecordResponse:
    return _to_record_response(get_learning_automation_record(session, learning_automation_id))
