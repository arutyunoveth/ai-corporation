from datetime import datetime

from src.shared.enums import DeliveryLaunchStatus, LaunchRecommendation, RiskSeverity
from src.shared.types.common import APIModel


class BuildDeliveryLaunchRequest(APIModel):
    deal_id: str
    outcome_intake_set_id: str


class LaunchDeliveryRequest(APIModel):
    delivery_launch_set_id: str
    launched_by_ref: str | None = None


class DeliveryLaunchFlagResponse(APIModel):
    flag_code: str
    severity: RiskSeverity
    summary: str
    source_ref: str | None
    created_at: datetime


class DeliveryLaunchRecordResponse(APIModel):
    delivery_launch_id: str
    delivery_launch_set_id: str
    launch_recommendation: LaunchRecommendation
    summary_text: str
    created_at: datetime
    updated_at: datetime
    flags: list[DeliveryLaunchFlagResponse]


class DeliveryLaunchSetResponse(APIModel):
    delivery_launch_set_id: str
    deal_id: str
    outcome_intake_set_id: str
    launch_status: DeliveryLaunchStatus
    created_at: datetime
    updated_at: datetime
    records: list[DeliveryLaunchRecordResponse]
