from fastapi import APIRouter, Query, status

from src.modules.integration_tasks.schemas import (
    BuildIntegrationTaskRequest,
    IntegrationTaskBindingResponse,
    IntegrationTaskRecordResponse,
    IntegrationTaskSetResponse,
)
from src.modules.integration_tasks.service import (
    build_integration_tasks,
    get_integration_task_record,
    get_integration_task_set,
    list_integration_task_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import WorkspaceScopeType

router = APIRouter(tags=["integration-tasks"])


def _to_binding_response(item) -> IntegrationTaskBindingResponse:
    return IntegrationTaskBindingResponse.model_validate(item)


def _to_record_response(result: tuple) -> IntegrationTaskRecordResponse:
    record, bindings = result
    return IntegrationTaskRecordResponse(
        integration_task_id=record.integration_task_id,
        integration_task_set_id=record.integration_task_set_id,
        connector_registry_id=record.connector_registry_id,
        action_queue_id=record.action_queue_id,
        task_type=record.task_type,
        task_payload_json=record.task_payload_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
        bindings=[_to_binding_response(item) for item in bindings],
    )


def _to_set_response(result: tuple) -> IntegrationTaskSetResponse:
    task_set, records = result
    return IntegrationTaskSetResponse(
        integration_task_set_id=task_set.integration_task_set_id,
        scope_type=task_set.scope_type,
        scope_ref=task_set.scope_ref,
        task_status=task_set.task_status,
        created_at=task_set.created_at,
        updated_at=task_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/integration-tasks/build", response_model=IntegrationTaskSetResponse, status_code=status.HTTP_201_CREATED)
def build_integration_tasks_route(
    payload: BuildIntegrationTaskRequest,
    session: DBSession,
) -> IntegrationTaskSetResponse:
    task_set = build_integration_tasks(session, payload)
    return _to_set_response(get_integration_task_set(session, task_set.integration_task_set_id))


@router.get("/integration-tasks/{integration_task_set_id}", response_model=IntegrationTaskSetResponse)
def get_integration_task_set_route(integration_task_set_id: str, session: DBSession) -> IntegrationTaskSetResponse:
    return _to_set_response(get_integration_task_set(session, integration_task_set_id))


@router.get("/integration-tasks", response_model=list[IntegrationTaskSetResponse])
def list_integration_task_sets_route(
    session: DBSession,
    scope_type: WorkspaceScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[IntegrationTaskSetResponse]:
    return [_to_set_response(item) for item in list_integration_task_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/integration-tasks/records/{integration_task_id}", response_model=IntegrationTaskRecordResponse)
def get_integration_task_record_route(integration_task_id: str, session: DBSession) -> IntegrationTaskRecordResponse:
    return _to_record_response(get_integration_task_record(session, integration_task_id))
