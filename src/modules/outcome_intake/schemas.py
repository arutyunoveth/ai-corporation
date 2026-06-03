from datetime import datetime

from pydantic import Field

from src.shared.enums import OutcomeBindingType, OutcomeCode, OutcomeStatus
from src.shared.types.common import APIModel


class OutcomeIntakeBindingInput(APIModel):
    artifact_ref: str
    binding_type: OutcomeBindingType


class RegisterOutcomeIntakeRequest(APIModel):
    deal_id: str
    post_submission_tracker_set_id: str
    outcome_code: OutcomeCode
    effective_at: datetime | None = None
    rationale: str
    bindings: list[OutcomeIntakeBindingInput] = Field(default_factory=list)


class OutcomeIntakeBindingResponse(APIModel):
    artifact_ref: str
    binding_type: OutcomeBindingType
    created_at: datetime


class OutcomeIntakeRecordResponse(APIModel):
    outcome_intake_id: str
    outcome_intake_set_id: str
    outcome_code: OutcomeCode
    effective_at: datetime
    rationale: str
    created_at: datetime
    updated_at: datetime
    bindings: list[OutcomeIntakeBindingResponse]


class OutcomeIntakeSetResponse(APIModel):
    outcome_intake_set_id: str
    deal_id: str
    post_submission_tracker_set_id: str
    outcome_status: OutcomeStatus
    created_at: datetime
    updated_at: datetime
    records: list[OutcomeIntakeRecordResponse]
