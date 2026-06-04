from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.acceptance_control.models import (
    AcceptanceControlRecord,
    AcceptanceControlSet,
    AcceptanceRemark,
    AcceptanceResolutionItem,
)
from src.modules.acceptance_control.schemas import BuildAcceptanceControlRequest
from src.modules.event_log.service import append_event_record
from src.modules.incident_register.models import IncidentRegisterSet
from src.modules.logistics_tracking.models import LogisticsTrackingSet
from src.shared.db.base import utcnow
from src.shared.delivery_recovery_package import load_delivery_helper_context
from src.shared.enums import (
    AcceptanceResolutionState,
    AcceptanceStatus,
    EventSeverity,
    LogisticsStatus,
    RiskSeverity,
    ShippingAcceptanceState,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_acceptance_control_id, next_acceptance_control_set_id


def _get_set(session: Session, acceptance_control_set_id: str) -> AcceptanceControlSet:
    record = session.scalar(
        select(AcceptanceControlSet).where(
            AcceptanceControlSet.acceptance_control_set_id == acceptance_control_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Acceptance control set '{acceptance_control_set_id}' was not found")
    return record


def _get_record(session: Session, acceptance_control_id: str) -> AcceptanceControlRecord:
    record = session.scalar(
        select(AcceptanceControlRecord).where(
            AcceptanceControlRecord.acceptance_control_id == acceptance_control_id
        )
    )
    if not record:
        raise NotFoundError(f"Acceptance control record '{acceptance_control_id}' was not found")
    return record


def _get_records(session: Session, acceptance_control_set_id: str) -> list[AcceptanceControlRecord]:
    return list(
        session.scalars(
            select(AcceptanceControlRecord)
            .where(AcceptanceControlRecord.acceptance_control_set_id == acceptance_control_set_id)
            .order_by(AcceptanceControlRecord.created_at.asc(), AcceptanceControlRecord.id.asc())
        )
    )


def _get_remarks(session: Session, acceptance_control_id: str) -> list[AcceptanceRemark]:
    return list(
        session.scalars(
            select(AcceptanceRemark)
            .where(AcceptanceRemark.acceptance_control_id == acceptance_control_id)
            .order_by(AcceptanceRemark.created_at.asc(), AcceptanceRemark.id.asc())
        )
    )


def _get_resolution_items(session: Session, acceptance_control_id: str) -> list[AcceptanceResolutionItem]:
    return list(
        session.scalars(
            select(AcceptanceResolutionItem)
            .where(AcceptanceResolutionItem.acceptance_control_id == acceptance_control_id)
            .order_by(AcceptanceResolutionItem.created_at.asc(), AcceptanceResolutionItem.id.asc())
        )
    )


def _latest_logistics_set(session: Session, deal_id: str) -> LogisticsTrackingSet | None:
    return session.scalar(
        select(LogisticsTrackingSet)
        .where(LogisticsTrackingSet.deal_id == deal_id)
        .order_by(LogisticsTrackingSet.created_at.desc(), LogisticsTrackingSet.id.desc())
    )


def _latest_incident_register_set(session: Session, deal_id: str) -> IncidentRegisterSet | None:
    return session.scalar(
        select(IncidentRegisterSet)
        .where(IncidentRegisterSet.deal_id == deal_id)
        .order_by(IncidentRegisterSet.created_at.desc(), IncidentRegisterSet.id.desc())
    )


def build_acceptance_control(session: Session, payload: BuildAcceptanceControlRequest) -> AcceptanceControlSet:
    logistics_set = _latest_logistics_set(session, payload.deal_id)
    if not logistics_set:
        raise ValidationError("Acceptance control requires canonical logistics tracking")

    incident_set = _latest_incident_register_set(session, payload.deal_id)
    helper_context = load_delivery_helper_context(session, payload.deal_id)

    acceptance_status = AcceptanceStatus.PENDING
    resolution_state = AcceptanceResolutionState.OPEN
    summary_text = "Acceptance dossier opened and awaiting customer confirmation."
    remark_text = "Validate received goods and issue acceptance act."
    remark_severity = RiskSeverity.LOW

    if helper_context.shipping_record:
        state = ShippingAcceptanceState(helper_context.shipping_record.current_state)
        if state == ShippingAcceptanceState.ACCEPTED:
            acceptance_status = AcceptanceStatus.ACCEPTED
            resolution_state = AcceptanceResolutionState.RESOLVED
            summary_text = "Acceptance confirmed from helper shipping/acceptance context."
            remark_text = "Acceptance act is ready to archive."
        elif state == ShippingAcceptanceState.REJECTED:
            acceptance_status = AcceptanceStatus.REJECTED
            summary_text = "Acceptance issue detected from helper shipping context."
            remark_text = "Resolve rejection remarks before closing acceptance."
            remark_severity = RiskSeverity.HIGH
        elif state == ShippingAcceptanceState.DELIVERED:
            acceptance_status = AcceptanceStatus.PENDING

    if logistics_set.logistics_status == LogisticsStatus.FAILED:
        acceptance_status = AcceptanceStatus.NEEDS_REVIEW
        summary_text = "Acceptance cannot proceed until logistics deviations are resolved."
        remark_text = "Investigate failed delivery before acceptance."
        remark_severity = RiskSeverity.HIGH
    elif incident_set:
        acceptance_status = AcceptanceStatus.NEEDS_REVIEW
        summary_text = "Acceptance requires review because canonical incident register is open."
        remark_text = "Resolve open incident context before final acceptance."
        remark_severity = RiskSeverity.MEDIUM

    control_set = AcceptanceControlSet(
        acceptance_control_set_id=next_acceptance_control_set_id(
            session, AcceptanceControlSet.acceptance_control_set_id
        ),
        deal_id=payload.deal_id,
        acceptance_status=acceptance_status,
    )
    session.add(control_set)
    session.flush()
    try:
        record = AcceptanceControlRecord(
            acceptance_control_id=next_acceptance_control_id(
                session, AcceptanceControlRecord.acceptance_control_id
            ),
            acceptance_control_set_id=control_set.acceptance_control_set_id,
            summary_text=summary_text,
            resolution_state=resolution_state,
        )
        session.add(record)
        session.flush()
        session.add(
            AcceptanceRemark(
                acceptance_control_id=record.acceptance_control_id,
                remark_code="ACCEPTANCE_REMARK_001",
                remark_text=remark_text,
                severity=remark_severity,
            )
        )
        session.add(
            AcceptanceResolutionItem(
                acceptance_control_id=record.acceptance_control_id,
                item_code="RESOLUTION_001",
                resolution_text=(
                    "Archive acceptance act."
                    if acceptance_status == AcceptanceStatus.ACCEPTED
                    else "Resolve acceptance remark and re-run canonical acceptance control."
                ),
            )
        )
        control_set.updated_at = utcnow()
        session.add(control_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="acceptance_control_built",
            source_module_id="M-041",
            severity=EventSeverity.INFO,
            payload_json={
                "acceptance_control_set_id": control_set.acceptance_control_set_id,
                "acceptance_control_id": record.acceptance_control_id,
            },
        )
        session.commit()
    except Exception as exc:
        control_set.acceptance_status = AcceptanceStatus.NEEDS_REVIEW
        control_set.updated_at = utcnow()
        session.add(control_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="acceptance_control_failed",
            source_module_id="M-041",
            severity=EventSeverity.HIGH,
            payload_json={"acceptance_control_set_id": control_set.acceptance_control_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(control_set)
    return control_set


def get_acceptance_control_set(
    session: Session,
    acceptance_control_set_id: str,
) -> tuple[AcceptanceControlSet, list[tuple[AcceptanceControlRecord, list[AcceptanceRemark], list[AcceptanceResolutionItem]]]]:
    control_set = _get_set(session, acceptance_control_set_id)
    records = _get_records(session, acceptance_control_set_id)
    return control_set, [
        (record, _get_remarks(session, record.acceptance_control_id), _get_resolution_items(session, record.acceptance_control_id))
        for record in records
    ]


def list_acceptance_control_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[AcceptanceControlSet, list[tuple[AcceptanceControlRecord, list[AcceptanceRemark], list[AcceptanceResolutionItem]]]]]:
    query = select(AcceptanceControlSet).order_by(
        AcceptanceControlSet.created_at.desc(), AcceptanceControlSet.id.desc()
    )
    if deal_id:
        query = query.where(AcceptanceControlSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_acceptance_control_set(session, item.acceptance_control_set_id) for item in sets]


def get_acceptance_control_record(
    session: Session,
    acceptance_control_id: str,
) -> tuple[AcceptanceControlRecord, list[AcceptanceRemark], list[AcceptanceResolutionItem]]:
    record = _get_record(session, acceptance_control_id)
    return record, _get_remarks(session, acceptance_control_id), _get_resolution_items(session, acceptance_control_id)
