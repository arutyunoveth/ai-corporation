from datetime import datetime

from pydantic import Field

from src.shared.types.common import APIModel


class PilotOperatorActionRecord(APIModel):
    action: str
    decision_code: str
    actor_ref: str | None = None
    rationale: str | None = None
    recorded_at: datetime


class PilotEvidenceBlocker(APIModel):
    severity: str
    summary: str


class PilotEvidenceMetrics(APIModel):
    operator_action_count: int = 0
    blocker_count: int = 0
    generated_report_count: int = 0
    customer_usefulness_score: int | None = Field(default=None, ge=1, le=5)
    estimated_time_saved_minutes: int | None = Field(default=None, ge=0)


class PilotEvidenceRecord(APIModel):
    pilot_run_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    fixture_name: str = Field(min_length=1)
    deal_id: str = Field(min_length=1)
    provider_mode: str = Field(min_length=1)
    started_at: datetime
    ended_at: datetime
    generated_report_refs: dict[str, str] = Field(default_factory=dict)
    operator_actions: list[PilotOperatorActionRecord] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    blockers: list[PilotEvidenceBlocker] = Field(default_factory=list)
    customer_usefulness_score: int | None = Field(default=None, ge=1, le=5)
    estimated_time_saved_minutes: int | None = Field(default=None, ge=0)
    final_outcome: str = Field(min_length=1)
    metrics: PilotEvidenceMetrics
