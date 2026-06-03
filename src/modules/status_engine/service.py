from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.deal_registry.models import Deal
from src.modules.event_log.service import append_event_record
from src.modules.status_engine.models import DealStatusHistory, StatusTransitionRule
from src.modules.status_engine.schemas import ApplyTransitionRequest, ValidateTransitionRequest
from src.shared.db.base import utcnow
from src.shared.enums import ChangedByType, DealStatus, EventSeverity, TransitionType
from src.shared.errors import NotFoundError, ValidationError

DEFAULT_TRANSITIONS: list[tuple[DealStatus, DealStatus]] = [
    (DealStatus.NEW, DealStatus.CANDIDATE),
    (DealStatus.CANDIDATE, DealStatus.DOCS_ANALYSIS),
    (DealStatus.CANDIDATE, DealStatus.REJECTED_EARLY),
    (DealStatus.DOCS_ANALYSIS, DealStatus.SUPPLIER_SOURCING),
    (DealStatus.DOCS_ANALYSIS, DealStatus.REJECTED_EARLY),
    (DealStatus.SUPPLIER_SOURCING, DealStatus.ECONOMICS_REVIEW),
    (DealStatus.ECONOMICS_REVIEW, DealStatus.WAITING_CEO_APPROVAL_TO_BID),
    (DealStatus.WAITING_CEO_APPROVAL_TO_BID, DealStatus.BID_PREPARATION),
    (DealStatus.WAITING_CEO_APPROVAL_TO_BID, DealStatus.DECLINED_TO_BID),
    (DealStatus.BID_PREPARATION, DealStatus.PRE_SUBMISSION),
    (DealStatus.PRE_SUBMISSION, DealStatus.SUBMISSION),
    (DealStatus.SUBMISSION, DealStatus.POST_SUBMISSION),
    (DealStatus.POST_SUBMISSION, DealStatus.OUTCOME_CAPTURE),
]


def append_initial_status_history(session: Session, *, deal_id: str, to_status: DealStatus) -> DealStatusHistory:
    history = DealStatusHistory(
        deal_id=deal_id,
        from_status=None,
        to_status=to_status,
        changed_by_type=ChangedByType.SYSTEM,
        changed_by_ref="M-001",
        reason_code="deal_created",
        reason_text="Initial status assigned at deal creation",
        is_override=False,
    )
    session.add(history)
    session.flush()
    return history


def seed_default_rules(session: Session) -> int:
    created = 0
    for from_status, to_status in DEFAULT_TRANSITIONS:
        exists = session.scalar(
            select(StatusTransitionRule).where(
                StatusTransitionRule.from_status == from_status,
                StatusTransitionRule.to_status == to_status,
            )
        )
        if exists:
            continue
        session.add(
            StatusTransitionRule(
                from_status=from_status,
                to_status=to_status,
                is_enabled=True,
                transition_type=TransitionType.BOTH,
                notes="Seeded from Sprint 1 catalog",
            )
        )
        created += 1
    session.commit()
    return created


def _get_deal(session: Session, deal_id: str) -> Deal:
    deal = session.scalar(select(Deal).where(Deal.deal_id == deal_id, Deal.is_deleted.is_(False)))
    if not deal:
        raise NotFoundError(f"Deal '{deal_id}' was not found")
    return deal


def validate_transition(session: Session, payload: ValidateTransitionRequest) -> tuple[bool, str | None]:
    deal = _get_deal(session, payload.deal_id)
    effective_from_status = payload.from_status or deal.current_status
    if deal.current_status != effective_from_status:
        return False, "deal.current_status does not match requested from_status"
    rule = session.scalar(
        select(StatusTransitionRule).where(
            StatusTransitionRule.from_status == effective_from_status,
            StatusTransitionRule.to_status == payload.to_status,
            StatusTransitionRule.is_enabled.is_(True),
        )
    )
    if not rule:
        return False, "transition rule does not exist or is disabled"
    return True, None


def apply_transition(session: Session, payload: ApplyTransitionRequest) -> DealStatusHistory:
    deal = _get_deal(session, payload.deal_id)
    effective_from_status = payload.from_status or DealStatus(deal.current_status)
    allowed, reason = validate_transition(
        session,
        ValidateTransitionRequest(
            deal_id=payload.deal_id,
            from_status=effective_from_status,
            to_status=payload.to_status,
        ),
    )
    if not allowed:
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="deal_status_transition_blocked",
            source_module_id="M-002",
            severity=EventSeverity.WARNING,
            payload_json={
                "from_status": str(effective_from_status),
                "to_status": str(payload.to_status),
                "reason": reason,
            },
        )
        session.commit()
        raise ValidationError(reason or "transition is blocked")
    history = DealStatusHistory(
        deal_id=payload.deal_id,
        from_status=effective_from_status,
        to_status=payload.to_status,
        changed_by_type=payload.changed_by_type,
        changed_by_ref=payload.changed_by_ref,
        reason_code=payload.reason_code,
        reason_text=payload.reason_text,
        is_override=payload.is_override,
    )
    session.add(history)
    deal.current_status = payload.to_status
    deal.updated_at = utcnow()
    session.add(deal)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="deal_status_changed",
        source_module_id="M-002",
        severity=EventSeverity.INFO,
        payload_json={
            "from_status": str(effective_from_status),
            "to_status": str(payload.to_status),
            "changed_by_type": str(payload.changed_by_type),
            "changed_by_ref": payload.changed_by_ref,
            "reason_code": payload.reason_code,
            "reason_text": payload.reason_text,
            "is_override": payload.is_override,
        },
    )
    session.commit()
    session.refresh(history)
    return history


def get_status_history(session: Session, deal_id: str) -> list[DealStatusHistory]:
    _get_deal(session, deal_id)
    return list(
        session.scalars(
            select(DealStatusHistory)
            .where(DealStatusHistory.deal_id == deal_id)
            .order_by(DealStatusHistory.created_at.asc(), DealStatusHistory.id.asc())
        )
    )

