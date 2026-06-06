from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from src.shared.types.common import APIModel


class FeedbackSource(StrEnum):
    operator_observation = "operator_observation"
    partner_call = "partner_call"
    partner_written_feedback = "partner_written_feedback"
    internal_review = "internal_review"


class FeedbackType(StrEnum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"
    mixed = "mixed"
    blocked = "blocked"


class NextAction(StrEnum):
    iterate_report = "iterate_report"
    revise_workflow = "revise_workflow"
    request_more_data = "request_more_data"
    prepare_paid_pilot_offer = "prepare_paid_pilot_offer"
    pause_partner = "pause_partner"
    reject_use_case = "reject_use_case"


class FinalDecision(StrEnum):
    continue_design_partner = "continue_design_partner"
    offer_discounted_paid_pilot = "offer_discounted_paid_pilot"
    not_ready = "not_ready"
    pause = "pause"
    stop = "stop"


class FeedbackRecord(APIModel):
    feedback_id: str = Field(min_length=1)
    partner_workspace_id: str = Field(min_length=1)
    export_package_id_or_pilot_run_id: str = Field(min_length=1)
    feedback_source: FeedbackSource = FeedbackSource.operator_observation
    feedback_type: FeedbackType = FeedbackType.neutral
    usefulness_score: int | None = Field(default=None, ge=1, le=5)
    clarity_score: int | None = Field(default=None, ge=1, le=5)
    trust_score: int | None = Field(default=None, ge=1, le=5)
    missing_information: str = ""
    incorrect_or_unclear_sections: str = ""
    would_pay_signal: bool | None = None
    operator_notes: str = ""
    next_action: NextAction = NextAction.iterate_report
    created_at: datetime


class OutcomeRecord(APIModel):
    outcome_id: str = Field(min_length=1)
    partner_workspace_id: str = Field(min_length=1)
    pilot_run_id: str = Field(min_length=1)
    final_decision: FinalDecision = FinalDecision.continue_design_partner
    decision_reason: str = ""
    pilot_value_evidence: str = ""
    conversion_readiness: str = ""
    recommended_next_step: str = ""
    created_at: datetime
