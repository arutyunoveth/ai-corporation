import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.models import DecisionRecord
from src.modules.pilot_evidence.schemas import (
    PilotEvidenceBlocker,
    PilotEvidenceMetrics,
    PilotEvidenceRecord,
    PilotOperatorActionRecord,
)
from src.shared.db.base import utcnow


def build_pilot_evidence_record(
    session: Session,
    *,
    scenario_id: str,
    fixture_name: str,
    deal_id: str,
    provider_mode: str,
    started_at,
    ended_at,
    generated_report_refs: dict[str, str],
    review_notes: list[str] | None = None,
    blockers: list[dict] | None = None,
    customer_usefulness_score: int | None = None,
    estimated_time_saved_minutes: int | None = None,
    final_outcome: str,
) -> PilotEvidenceRecord:
    decisions = list(
        session.scalars(
            select(DecisionRecord)
            .where(DecisionRecord.deal_id == deal_id)
            .order_by(DecisionRecord.created_at.asc(), DecisionRecord.id.asc())
        )
    )
    operator_actions = [
        PilotOperatorActionRecord(
            action=str((decision.payload_json or {}).get("action") or decision.decision_code),
            decision_code=decision.decision_code,
            actor_ref=decision.decided_by_ref,
            rationale=decision.rationale,
            recorded_at=decision.created_at,
        )
        for decision in decisions
    ]
    blocker_models = [PilotEvidenceBlocker.model_validate(item) for item in (blockers or [])]
    metrics = PilotEvidenceMetrics(
        operator_action_count=len(operator_actions),
        blocker_count=len(blocker_models),
        generated_report_count=len(generated_report_refs),
        customer_usefulness_score=customer_usefulness_score,
        estimated_time_saved_minutes=estimated_time_saved_minutes,
    )
    return PilotEvidenceRecord(
        pilot_run_id=f"PILOT-RUN-{utcnow().strftime('%Y%m%d%H%M%S')}",
        scenario_id=scenario_id,
        fixture_name=fixture_name,
        deal_id=deal_id,
        provider_mode=provider_mode,
        started_at=started_at,
        ended_at=ended_at,
        generated_report_refs=generated_report_refs,
        operator_actions=operator_actions,
        review_notes=review_notes or [],
        blockers=blocker_models,
        customer_usefulness_score=customer_usefulness_score,
        estimated_time_saved_minutes=estimated_time_saved_minutes,
        final_outcome=final_outcome,
        metrics=metrics,
    )


def render_pilot_evidence_markdown(record: PilotEvidenceRecord) -> str:
    report_lines = "\n".join(
        f"- {label}: {path}" for label, path in sorted(record.generated_report_refs.items())
    ) or "- none"
    action_lines = "\n".join(
        f"- {item.recorded_at.isoformat()} | {item.decision_code} | {item.action} | {item.actor_ref or 'n/a'}"
        for item in record.operator_actions
    ) or "- none"
    note_lines = "\n".join(f"- {item}" for item in record.review_notes) or "- none"
    blocker_lines = "\n".join(f"- [{item.severity}] {item.summary}" for item in record.blockers) or "- none"

    return (
        "# Pilot Evidence Ledger\n\n"
        f"- Pilot run ID: {record.pilot_run_id}\n"
        f"- Scenario ID: {record.scenario_id}\n"
        f"- Fixture name: {record.fixture_name}\n"
        f"- Deal ID: {record.deal_id}\n"
        f"- Provider mode: {record.provider_mode}\n"
        f"- Started at (UTC): {record.started_at.isoformat()}\n"
        f"- Ended at (UTC): {record.ended_at.isoformat()}\n"
        f"- Final outcome: {record.final_outcome}\n"
        f"- Customer usefulness score: {record.customer_usefulness_score}\n"
        f"- Estimated time saved (minutes): {record.estimated_time_saved_minutes}\n\n"
        "## Generated Report Refs\n"
        f"{report_lines}\n\n"
        "## Operator Actions\n"
        f"{action_lines}\n\n"
        "## Review Notes\n"
        f"{note_lines}\n\n"
        "## Blockers\n"
        f"{blocker_lines}\n\n"
        "## Metrics\n"
        f"- operator_action_count: {record.metrics.operator_action_count}\n"
        f"- blocker_count: {record.metrics.blocker_count}\n"
        f"- generated_report_count: {record.metrics.generated_report_count}\n"
    )


def write_pilot_evidence_bundle(output_dir: str | Path, record: PilotEvidenceRecord) -> tuple[Path, Path]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / f"{record.deal_id}_pilot_evidence.json"
    markdown_path = target_dir / f"{record.deal_id}_pilot_evidence.md"
    json_path.write_text(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_pilot_evidence_markdown(record), encoding="utf-8")
    return json_path, markdown_path
