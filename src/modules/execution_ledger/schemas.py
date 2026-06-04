from datetime import datetime

from src.shared.enums import ExecutionLedgerStatus, ExecutionStatus, WorkspaceScopeType
from src.shared.types.common import APIModel


class BuildExecutionLedgerRequest(APIModel):
    scope_type: WorkspaceScopeType
    scope_ref: str


class StartExecutionLedgerRequest(APIModel):
    execution_ledger_id: str
    executed_by_ref: str | None = None


class ExecutionResultRecordResponse(APIModel):
    result_code: str
    result_summary: str
    artifact_ref: str | None
    created_at: datetime


class ExecutionLedgerRecordResponse(APIModel):
    execution_ledger_id: str
    execution_ledger_set_id: str
    action_queue_id: str
    integration_task_id: str
    execution_status: ExecutionStatus
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
    results: list[ExecutionResultRecordResponse]


class ExecutionLedgerSetResponse(APIModel):
    execution_ledger_set_id: str
    scope_type: WorkspaceScopeType
    scope_ref: str
    ledger_status: ExecutionLedgerStatus
    created_at: datetime
    updated_at: datetime
    records: list[ExecutionLedgerRecordResponse]
