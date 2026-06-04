from datetime import datetime

from src.shared.enums import (
    ExternalExecutionStatus,
    ExternalGatewayStatus,
    GatewayActionType,
    WorkspaceScopeType,
)
from src.shared.types.common import APIModel


class BuildExternalExecutionRequest(APIModel):
    scope_type: WorkspaceScopeType
    scope_ref: str


class StartExternalExecutionRequest(APIModel):
    external_execution_id: str


class ExternalExecutionResultResponse(APIModel):
    result_code: str
    result_summary: str
    response_payload_json: dict
    artifact_ref: str | None
    created_at: datetime


class ExternalExecutionRecordResponse(APIModel):
    external_execution_id: str
    external_execution_set_id: str
    integration_task_id: str
    execution_ledger_id: str
    gateway_action_type: GatewayActionType
    request_payload_json: dict
    execution_status: ExternalExecutionStatus
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
    results: list[ExternalExecutionResultResponse]


class ExternalExecutionSetResponse(APIModel):
    external_execution_set_id: str
    scope_type: WorkspaceScopeType
    scope_ref: str
    gateway_status: ExternalGatewayStatus
    created_at: datetime
    updated_at: datetime
    records: list[ExternalExecutionRecordResponse]
