from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.contract_negotiation.models import (
    ContractNegotiationComment,
    ContractNegotiationIssue,
    ContractNegotiationRecord,
    ContractNegotiationSet,
)
from src.modules.contract_negotiation.schemas import BuildContractNegotiationRequest
from src.modules.contract_risks.models import ContractRiskRecord, ContractRiskSet
from src.modules.document_store.models import DocumentArtifact
from src.modules.event_log.service import append_event_record
from src.modules.outcome_intake.models import OutcomeIntakeBinding, OutcomeIntakeRecord, OutcomeIntakeSet
from src.shared.db.base import utcnow
from src.shared.enums import ContractNegotiationStatus, EventSeverity, OutcomeCode, RiskSeverity
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_contract_negotiation_id, next_contract_negotiation_set_id


def _get_set(session: Session, contract_negotiation_set_id: str) -> ContractNegotiationSet:
    record = session.scalar(
        select(ContractNegotiationSet).where(
            ContractNegotiationSet.contract_negotiation_set_id == contract_negotiation_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Contract negotiation set '{contract_negotiation_set_id}' was not found")
    return record


def _get_record(session: Session, contract_negotiation_id: str) -> ContractNegotiationRecord:
    record = session.scalar(
        select(ContractNegotiationRecord).where(
            ContractNegotiationRecord.contract_negotiation_id == contract_negotiation_id
        )
    )
    if not record:
        raise NotFoundError(f"Contract negotiation record '{contract_negotiation_id}' was not found")
    return record


def _get_records(session: Session, contract_negotiation_set_id: str) -> list[ContractNegotiationRecord]:
    return list(
        session.scalars(
            select(ContractNegotiationRecord)
            .where(ContractNegotiationRecord.contract_negotiation_set_id == contract_negotiation_set_id)
            .order_by(ContractNegotiationRecord.created_at.asc(), ContractNegotiationRecord.id.asc())
        )
    )


def _get_issues(session: Session, contract_negotiation_id: str) -> list[ContractNegotiationIssue]:
    return list(
        session.scalars(
            select(ContractNegotiationIssue)
            .where(ContractNegotiationIssue.contract_negotiation_id == contract_negotiation_id)
            .order_by(ContractNegotiationIssue.created_at.asc(), ContractNegotiationIssue.id.asc())
        )
    )


def _get_comments(session: Session, contract_negotiation_id: str) -> list[ContractNegotiationComment]:
    return list(
        session.scalars(
            select(ContractNegotiationComment)
            .where(ContractNegotiationComment.contract_negotiation_id == contract_negotiation_id)
            .order_by(ContractNegotiationComment.created_at.asc(), ContractNegotiationComment.id.asc())
        )
    )


def _latest_won_outcome(
    session: Session, deal_id: str
) -> tuple[OutcomeIntakeSet, OutcomeIntakeRecord, list[OutcomeIntakeBinding]]:
    outcome_set = session.scalar(
        select(OutcomeIntakeSet)
        .where(OutcomeIntakeSet.deal_id == deal_id)
        .order_by(OutcomeIntakeSet.created_at.desc(), OutcomeIntakeSet.id.desc())
        .limit(1)
    )
    if not outcome_set:
        raise ValidationError("Contract negotiation requires explicit WON outcome context")
    outcome_record = session.scalar(
        select(OutcomeIntakeRecord)
        .where(OutcomeIntakeRecord.outcome_intake_set_id == outcome_set.outcome_intake_set_id)
        .order_by(OutcomeIntakeRecord.effective_at.desc(), OutcomeIntakeRecord.id.desc())
        .limit(1)
    )
    if not outcome_record or outcome_record.outcome_code != OutcomeCode.WON:
        raise ValidationError("Contract negotiation can only be opened after a WON outcome")
    bindings = list(
        session.scalars(
            select(OutcomeIntakeBinding)
            .where(OutcomeIntakeBinding.outcome_intake_id == outcome_record.outcome_intake_id)
            .order_by(OutcomeIntakeBinding.created_at.asc(), OutcomeIntakeBinding.id.asc())
        )
    )
    return outcome_set, outcome_record, bindings


def _latest_contract_risks(
    session: Session, deal_id: str
) -> tuple[ContractRiskSet | None, list[ContractRiskRecord]]:
    risk_set = session.scalar(
        select(ContractRiskSet)
        .where(ContractRiskSet.deal_id == deal_id)
        .order_by(ContractRiskSet.created_at.desc(), ContractRiskSet.id.desc())
        .limit(1)
    )
    if not risk_set:
        return None, []
    records = list(
        session.scalars(
            select(ContractRiskRecord)
            .where(ContractRiskRecord.contract_risk_set_id == risk_set.contract_risk_set_id)
            .order_by(ContractRiskRecord.created_at.asc(), ContractRiskRecord.id.asc())
        )
    )
    return risk_set, records


def build_contract_negotiation(session: Session, payload: BuildContractNegotiationRequest) -> ContractNegotiationSet:
    outcome_set, outcome_record, bindings = _latest_won_outcome(session, payload.deal_id)
    risk_set, risk_records = _latest_contract_risks(session, payload.deal_id)

    negotiation_set = ContractNegotiationSet(
        contract_negotiation_set_id=next_contract_negotiation_set_id(
            session, ContractNegotiationSet.contract_negotiation_set_id
        ),
        deal_id=payload.deal_id,
        negotiation_status=ContractNegotiationStatus.OPEN,
    )
    session.add(negotiation_set)
    session.flush()
    try:
        bound_artifacts = []
        for binding in bindings:
            artifact = session.scalar(
                select(DocumentArtifact).where(DocumentArtifact.artifact_ref == binding.artifact_ref).limit(1)
            )
            if artifact:
                bound_artifacts.append(artifact)
        manifest = {
            "outcome_intake_set_id": outcome_set.outcome_intake_set_id,
            "outcome_intake_id": outcome_record.outcome_intake_id,
            "outcome_binding_count": len(bindings),
            "contract_risk_set_id": risk_set.contract_risk_set_id if risk_set else None,
            "artifact_refs": [artifact.artifact_ref for artifact in bound_artifacts],
        }
        summary_text = (
            f"Contract negotiation workspace opened for deal {payload.deal_id}; "
            f"won outcome recorded at {outcome_record.effective_at.isoformat()}."
        )
        record = ContractNegotiationRecord(
            contract_negotiation_id=next_contract_negotiation_id(
                session, ContractNegotiationRecord.contract_negotiation_id
            ),
            contract_negotiation_set_id=negotiation_set.contract_negotiation_set_id,
            summary_text=summary_text,
            negotiation_pack_manifest_json=manifest,
        )
        session.add(record)
        session.flush()
        issues_count = 0
        for risk_record in risk_records:
            issues_count += 1
            issue_text = f"{risk_record.summary} ({risk_record.clause_type})"
            session.add(
                ContractNegotiationIssue(
                    contract_negotiation_id=record.contract_negotiation_id,
                    issue_code=f"RISK_{risk_record.clause_type}",
                    issue_text=issue_text,
                    severity=risk_record.severity,
                )
            )
            session.add(
                ContractNegotiationComment(
                    contract_negotiation_id=record.contract_negotiation_id,
                    clause_ref=risk_record.clause_type,
                    comment_text=risk_record.notes or risk_record.summary,
                )
            )
        if not risk_records:
            session.add(
                ContractNegotiationComment(
                    contract_negotiation_id=record.contract_negotiation_id,
                    clause_ref="OUTCOME_CONTEXT",
                    comment_text="Workspace opened from winning outcome; no persisted contract risks were available.",
                )
            )
        negotiation_set.negotiation_status = (
            ContractNegotiationStatus.NEEDS_REVIEW if issues_count else ContractNegotiationStatus.READY_TO_NEGOTIATE
        )
        negotiation_set.updated_at = utcnow()
        session.add(negotiation_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="contract_negotiation_built",
            source_module_id="M-034",
            severity=EventSeverity.INFO,
            payload_json={
                "contract_negotiation_set_id": negotiation_set.contract_negotiation_set_id,
                "contract_negotiation_id": record.contract_negotiation_id,
                "issue_count": issues_count,
            },
        )
        session.commit()
    except Exception as exc:
        negotiation_set.negotiation_status = ContractNegotiationStatus.FAILED
        negotiation_set.updated_at = utcnow()
        session.add(negotiation_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="contract_negotiation_failed",
            source_module_id="M-034",
            severity=EventSeverity.HIGH,
            payload_json={"contract_negotiation_set_id": negotiation_set.contract_negotiation_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(negotiation_set)
    return negotiation_set


def get_contract_negotiation_set(
    session: Session,
    contract_negotiation_set_id: str,
) -> tuple[ContractNegotiationSet, list[tuple[ContractNegotiationRecord, list[ContractNegotiationIssue], list[ContractNegotiationComment]]]]:
    negotiation_set = _get_set(session, contract_negotiation_set_id)
    records = _get_records(session, contract_negotiation_set_id)
    return negotiation_set, [
        (record, _get_issues(session, record.contract_negotiation_id), _get_comments(session, record.contract_negotiation_id))
        for record in records
    ]


def list_contract_negotiation_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[ContractNegotiationSet, list[tuple[ContractNegotiationRecord, list[ContractNegotiationIssue], list[ContractNegotiationComment]]]]]:
    query = select(ContractNegotiationSet).order_by(
        ContractNegotiationSet.created_at.desc(), ContractNegotiationSet.id.desc()
    )
    if deal_id:
        query = query.where(ContractNegotiationSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_contract_negotiation_set(session, item.contract_negotiation_set_id) for item in sets]


def get_contract_negotiation_record(
    session: Session,
    contract_negotiation_id: str,
) -> tuple[ContractNegotiationRecord, list[ContractNegotiationIssue], list[ContractNegotiationComment]]:
    record = _get_record(session, contract_negotiation_id)
    return record, _get_issues(session, contract_negotiation_id), _get_comments(session, contract_negotiation_id)
