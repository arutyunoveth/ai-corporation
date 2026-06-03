from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.ceo_approval.models import CEOApprovalCondition, CEOApprovalRecord, CEOApprovalSet
from src.modules.ceo_approval.schemas import BuildCEOApprovalRequest, RecordCEODecisionRequest
from src.modules.event_log.models import DecisionRecord
from src.modules.event_log.service import append_event_record
from src.modules.finance_memo.service import get_finance_memo_set
from src.modules.integrated_risk_memo.service import get_integrated_risk_memo_set
from src.shared.db.base import utcnow
from src.shared.enums import ApprovalDecision, ApprovalStatus, DecisionByType, EventSeverity
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import (
    next_ceo_approval_id,
    next_ceo_approval_set_id,
    next_decision_id,
)
from src.shared.validation import require_non_empty, require_non_empty_list, require_same_reference


def _get_set(session: Session, ceo_approval_set_id: str) -> CEOApprovalSet:
    record = session.scalar(select(CEOApprovalSet).where(CEOApprovalSet.ceo_approval_set_id == ceo_approval_set_id))
    if not record:
        raise NotFoundError(f"CEO approval set '{ceo_approval_set_id}' was not found")
    return record


def _get_records(session: Session, ceo_approval_set_id: str) -> list[CEOApprovalRecord]:
    return list(
        session.scalars(
            select(CEOApprovalRecord)
            .where(CEOApprovalRecord.ceo_approval_set_id == ceo_approval_set_id)
            .order_by(CEOApprovalRecord.decided_at.asc(), CEOApprovalRecord.id.asc())
        )
    )


def _get_conditions(session: Session, ceo_approval_id: str) -> list[CEOApprovalCondition]:
    return list(
        session.scalars(
            select(CEOApprovalCondition)
            .where(CEOApprovalCondition.ceo_approval_id == ceo_approval_id)
            .order_by(CEOApprovalCondition.created_at.asc(), CEOApprovalCondition.id.asc())
        )
    )


def build_ceo_approval(session: Session, payload: BuildCEOApprovalRequest) -> CEOApprovalSet:
    finance_set, finance_records = get_finance_memo_set(session, payload.finance_memo_set_id)
    risk_memo_set, risk_memo_records = get_integrated_risk_memo_set(session, payload.integrated_risk_memo_set_id)
    require_same_reference(payload.deal_id, finance_set.deal_id, "deal_id")
    require_same_reference(payload.deal_id, risk_memo_set.deal_id, "deal_id")
    if not finance_records or not risk_memo_records:
        raise ValidationError("CEO approval package requires formal finance memo and integrated risk memo records")

    approval_set = CEOApprovalSet(
        ceo_approval_set_id=next_ceo_approval_set_id(session, CEOApprovalSet.ceo_approval_set_id),
        deal_id=payload.deal_id,
        finance_memo_set_id=finance_set.finance_memo_set_id,
        integrated_risk_memo_set_id=risk_memo_set.integrated_risk_memo_set_id,
        approval_status=ApprovalStatus.OPEN,
    )
    session.add(approval_set)
    session.flush()
    try:
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="ceo_approval_package_built",
            source_module_id="M-028",
            severity=EventSeverity.INFO,
            payload_json={
                "ceo_approval_set_id": approval_set.ceo_approval_set_id,
                "finance_memo_set_id": finance_set.finance_memo_set_id,
                "integrated_risk_memo_set_id": risk_memo_set.integrated_risk_memo_set_id,
            },
        )
        session.commit()
    except Exception as exc:
        approval_set.approval_status = ApprovalStatus.STALE
        approval_set.updated_at = utcnow()
        session.add(approval_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="ceo_approval_failed",
            source_module_id="M-028",
            severity=EventSeverity.HIGH,
            payload_json={"ceo_approval_set_id": approval_set.ceo_approval_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(approval_set)
    return approval_set


def record_ceo_decision(
    session: Session,
    payload: RecordCEODecisionRequest,
) -> CEOApprovalRecord:
    approval_set = _get_set(session, payload.ceo_approval_set_id)
    decision = str(payload.decision)
    if decision == str(ApprovalDecision.GO_WITH_CONDITIONS):
        require_non_empty_list(payload.conditions, "conditions")
    rationale = require_non_empty(payload.rationale, "rationale")

    approval_record = CEOApprovalRecord(
        ceo_approval_id=next_ceo_approval_id(session, CEOApprovalRecord.ceo_approval_id),
        ceo_approval_set_id=approval_set.ceo_approval_set_id,
        decision=payload.decision,
        decided_by_ref=payload.decided_by_ref.strip() if payload.decided_by_ref else None,
        rationale=rationale,
        decided_at=utcnow(),
    )
    session.add(approval_record)
    session.flush()
    for condition in payload.conditions:
        session.add(
            CEOApprovalCondition(
                ceo_approval_id=approval_record.ceo_approval_id,
                condition_code=require_non_empty(condition.condition_code, "condition_code"),
                condition_text=require_non_empty(condition.condition_text, "condition_text"),
            )
        )

    session.add(
        DecisionRecord(
            decision_id=next_decision_id(session, DecisionRecord.decision_id),
            deal_id=approval_set.deal_id,
            decision_code="CEO_APPROVAL_DECISION",
            decided_by_type=DecisionByType.HUMAN,
            decided_by_ref=approval_record.decided_by_ref,
            rationale=rationale,
            payload_json={
                "ceo_approval_id": approval_record.ceo_approval_id,
                "decision": decision,
                "condition_count": len(payload.conditions),
            },
        )
    )
    approval_set.approval_status = ApprovalStatus.DECIDED
    approval_set.updated_at = utcnow()
    session.add(approval_set)
    try:
        append_event_record(
            session,
            deal_id=approval_set.deal_id,
            event_code="decision_recorded",
            source_module_id="M-004",
            severity=EventSeverity.INFO,
            payload_json={
                "decision_code": "CEO_APPROVAL_DECISION",
                "ceo_approval_id": approval_record.ceo_approval_id,
            },
        )
        append_event_record(
            session,
            deal_id=approval_set.deal_id,
            event_code="ceo_decision_recorded",
            source_module_id="M-028",
            severity=EventSeverity.INFO,
            payload_json={
                "ceo_approval_set_id": approval_set.ceo_approval_set_id,
                "ceo_approval_id": approval_record.ceo_approval_id,
                "decision": decision,
            },
        )
        session.commit()
    except Exception as exc:
        append_event_record(
            session,
            deal_id=approval_set.deal_id,
            event_code="ceo_approval_failed",
            source_module_id="M-028",
            severity=EventSeverity.HIGH,
            payload_json={"ceo_approval_set_id": approval_set.ceo_approval_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(approval_record)
    return approval_record


def get_ceo_approval_set(
    session: Session,
    ceo_approval_set_id: str,
) -> tuple[CEOApprovalSet, list[tuple[CEOApprovalRecord, list[CEOApprovalCondition]]]]:
    approval_set = _get_set(session, ceo_approval_set_id)
    records = _get_records(session, ceo_approval_set_id)
    return approval_set, [(record, _get_conditions(session, record.ceo_approval_id)) for record in records]


def list_ceo_approval_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[CEOApprovalSet, list[tuple[CEOApprovalRecord, list[CEOApprovalCondition]]]]]:
    query = select(CEOApprovalSet).order_by(CEOApprovalSet.created_at.desc())
    if deal_id:
        query = query.where(CEOApprovalSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_ceo_approval_set(session, item.ceo_approval_set_id) for item in sets]


def get_ceo_approval_record(
    session: Session,
    ceo_approval_id: str,
) -> tuple[CEOApprovalRecord, list[CEOApprovalCondition]]:
    record = session.scalar(select(CEOApprovalRecord).where(CEOApprovalRecord.ceo_approval_id == ceo_approval_id))
    if not record:
        raise NotFoundError(f"CEO approval record '{ceo_approval_id}' was not found")
    return record, _get_conditions(session, ceo_approval_id)
