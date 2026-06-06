from datetime import datetime

from pydantic import Field

from src.shared.types.common import APIModel


class ControlledPilotDryRunScenarioResult(APIModel):
    fixture_name: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    deal_id: str = Field(min_length=1)
    provider_mode: str = Field(min_length=1)
    status: str = Field(min_length=1)
    final_outcome: str = Field(min_length=1)
    generated_report_refs: dict[str, str] = Field(default_factory=dict)
    evidence_json_path: str = Field(min_length=1)
    evidence_markdown_path: str = Field(min_length=1)
    blocker_count: int = 0


class ControlledPilotDryRunSummary(APIModel):
    started_at: datetime
    ended_at: datetime
    provider_mode: str = Field(min_length=1)
    scenario_results: list[ControlledPilotDryRunScenarioResult] = Field(default_factory=list)
    completed_scenarios: int = 0
    blocked_scenarios: int = 0
