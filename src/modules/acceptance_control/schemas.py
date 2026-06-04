from datetime import datetime

from src.shared.enums import AcceptanceResolutionState, AcceptanceStatus, RiskSeverity
from src.shared.types.common import APIModel


class BuildAcceptanceControlRequest(APIModel):
    deal_id: str


class AcceptanceRemarkResponse(APIModel):
    remark_code: str
    remark_text: str
    severity: RiskSeverity
    created_at: datetime


class AcceptanceResolutionItemResponse(APIModel):
    item_code: str
    resolution_text: str
    created_at: datetime


class AcceptanceControlRecordResponse(APIModel):
    acceptance_control_id: str
    summary_text: str
    resolution_state: AcceptanceResolutionState
    created_at: datetime
    updated_at: datetime
    remarks: list[AcceptanceRemarkResponse]
    resolution_items: list[AcceptanceResolutionItemResponse]


class AcceptanceControlSetResponse(APIModel):
    acceptance_control_set_id: str
    deal_id: str
    acceptance_status: AcceptanceStatus
    created_at: datetime
    updated_at: datetime
    records: list[AcceptanceControlRecordResponse]
