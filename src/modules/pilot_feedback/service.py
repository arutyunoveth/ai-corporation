from __future__ import annotations

from datetime import UTC, datetime

from src.modules.pilot_feedback.schemas import (
    FeedbackRecord,
    FeedbackSource,
    FeedbackType,
    FinalDecision,
    NextAction,
    OutcomeRecord,
)


def _generate_id(prefix: str) -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{ts}"


def create_feedback(
    *,
    partner_workspace_id: str,
    export_package_id_or_pilot_run_id: str,
    feedback_source: FeedbackSource = FeedbackSource.operator_observation,
    feedback_type: FeedbackType = FeedbackType.neutral,
    usefulness_score: int | None = None,
    clarity_score: int | None = None,
    trust_score: int | None = None,
    missing_information: str = "",
    incorrect_or_unclear_sections: str = "",
    would_pay_signal: bool | None = None,
    operator_notes: str = "",
    next_action: NextAction = NextAction.iterate_report,
) -> FeedbackRecord:
    return FeedbackRecord(
        feedback_id=_generate_id("FB"),
        partner_workspace_id=partner_workspace_id,
        export_package_id_or_pilot_run_id=export_package_id_or_pilot_run_id,
        feedback_source=feedback_source,
        feedback_type=feedback_type,
        usefulness_score=usefulness_score,
        clarity_score=clarity_score,
        trust_score=trust_score,
        missing_information=missing_information,
        incorrect_or_unclear_sections=incorrect_or_unclear_sections,
        would_pay_signal=would_pay_signal,
        operator_notes=operator_notes,
        next_action=next_action,
        created_at=datetime.now(UTC),
    )


def create_outcome(
    *,
    partner_workspace_id: str,
    pilot_run_id: str,
    final_decision: FinalDecision = FinalDecision.continue_design_partner,
    decision_reason: str = "",
    pilot_value_evidence: str = "",
    conversion_readiness: str = "",
    recommended_next_step: str = "",
) -> OutcomeRecord:
    return OutcomeRecord(
        outcome_id=_generate_id("OC"),
        partner_workspace_id=partner_workspace_id,
        pilot_run_id=pilot_run_id,
        final_decision=final_decision,
        decision_reason=decision_reason,
        pilot_value_evidence=pilot_value_evidence,
        conversion_readiness=conversion_readiness,
        recommended_next_step=recommended_next_step,
        created_at=datetime.now(UTC),
    )
