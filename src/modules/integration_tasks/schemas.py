from datetime import datetime

from src.shared.enums import (
    IntegrationTaskBindingType,
    IntegrationTaskStatus,
    IntegrationTaskType,
    WorkspaceScopeType,
)
from src.shared.types.common import APIModel


class BuildIntegrationTaskRequest(APIModel):
    scope_type: WorkspaceScopeType
    scope_ref: str


class IntegrationTaskBindingResponse(APIModel):
    source_ref: str
    binding_type: IntegrationTaskBindingType
    created_at: datetime


class IntegrationTaskRecordResponse(APIModel):
    integration_task_id: str
    integration_task_set_id: str
    connector_registry_id: str
    action_queue_id: str
    task_type: IntegrationTaskType
    task_payload_json: dict
    created_at: datetime
    updated_at: datetime
    bindings: list[IntegrationTaskBindingResponse]


class IntegrationTaskSetResponse(APIModel):
    integration_task_set_id: str
    scope_type: WorkspaceScopeType
    scope_ref: str
    task_status: IntegrationTaskStatus
    created_at: datetime
    updated_at: datetime
    records: list[IntegrationTaskRecordResponse]
