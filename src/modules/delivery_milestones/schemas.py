from datetime import datetime

from pydantic import Field

from src.shared.enums import DeliveryMilestoneStatus, MilestoneState
from src.shared.types.common import APIModel


class MilestoneSeed(APIModel):
    milestone_code: str
    milestone_name: str
    due_date: datetime | None = None
    milestone_state: MilestoneState = MilestoneState.PLANNED


class BuildDeliveryMilestonesRequest(APIModel):
    deal_id: str
    execution_command_set_id: str
    milestones: list[MilestoneSeed] = Field(default_factory=list)


class RegisterDeliveryMilestoneEventRequest(APIModel):
    delivery_milestone_id: str
    summary: str
    event_timestamp: datetime | None = None
    source_ref: str | None = None
    milestone_state: MilestoneState | None = None


class DeliveryMilestoneEventResponse(APIModel):
    delivery_milestone_event_id: str
    delivery_milestone_id: str
    event_timestamp: datetime
    summary: str
    source_ref: str | None
    created_at: datetime


class DeliveryMilestoneRecordResponse(APIModel):
    delivery_milestone_id: str
    delivery_milestone_set_id: str
    milestone_code: str
    milestone_name: str
    due_date: datetime | None
    milestone_state: MilestoneState
    created_at: datetime
    updated_at: datetime
    events: list[DeliveryMilestoneEventResponse]


class DeliveryMilestoneSetResponse(APIModel):
    delivery_milestone_set_id: str
    deal_id: str
    execution_command_set_id: str
    milestone_status: DeliveryMilestoneStatus
    created_at: datetime
    updated_at: datetime
    records: list[DeliveryMilestoneRecordResponse]
