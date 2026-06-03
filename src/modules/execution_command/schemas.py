from datetime import datetime

from src.shared.enums import ExecutionCommandStatus, ExecutionPhase
from src.shared.types.common import APIModel


class BuildExecutionCommandRequest(APIModel):
    deal_id: str
    delivery_launch_set_id: str


class ExecutionCommandBindingResponse(APIModel):
    source_object_type: str
    source_object_ref: str
    created_at: datetime


class ExecutionCommandRecordResponse(APIModel):
    execution_command_id: str
    execution_command_set_id: str
    current_phase: ExecutionPhase
    summary_text: str
    created_at: datetime
    updated_at: datetime


class ExecutionCommandSetResponse(APIModel):
    execution_command_set_id: str
    deal_id: str
    delivery_launch_set_id: str
    execution_status: ExecutionCommandStatus
    created_at: datetime
    updated_at: datetime
    bindings: list[ExecutionCommandBindingResponse]
    records: list[ExecutionCommandRecordResponse]
