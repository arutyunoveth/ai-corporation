from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.deal_closure.models import DealArchiveSnapshot, DealClosureRecord, DealClosureSet
from src.modules.deal_closure.schemas import BuildDealClosureRequest, CloseDealRequest
from src.modules.delivery_milestones.models import DeliveryMilestoneSet
from src.modules.event_log.service import append_event_record
from src.modules.payment_collection.models import PaymentCollectionSet
from src.modules.shipping_acceptance.models import ShippingAcceptanceSet
from src.modules.supplier_fulfillment.models import SupplierFulfillmentSet
from src.shared.closure_package import load_closure_package
from src.shared.db.base import utcnow
from src.shared.enums import (
    DealClosureCode,
    DealClosureStatus,
    EventSeverity,
    ExecutionCommandStatus,
    OutcomeCode,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import (
    next_archive_snapshot_id,
    next_deal_closure_id,
    next_deal_closure_set_id,
)
from src.shared.validation import require_same_reference


def _get_set(session: Session, deal_closure_set_id: str) -> DealClosureSet:
    record = session.scalar(select(DealClosureSet).where(DealClosureSet.deal_closure_set_id == deal_closure_set_id))
    if not record:
        raise NotFoundError(f"Deal closure set '{deal_closure_set_id}' was not found")
    return record


def _get_record(session: Session, deal_closure_id: str) -> DealClosureRecord:
    record = session.scalar(select(DealClosureRecord).where(DealClosureRecord.deal_closure_id == deal_closure_id))
    if not record:
        raise NotFoundError(f"Deal closure record '{deal_closure_id}' was not found")
    return record


def _get_records(session: Session, deal_closure_set_id: str) -> list[DealClosureRecord]:
    return list(
        session.scalars(
            select(DealClosureRecord)
            .where(DealClosureRecord.deal_closure_set_id == deal_closure_set_id)
            .order_by(DealClosureRecord.closed_at.asc(), DealClosureRecord.id.asc())
        )
    )


def _get_snapshots(session: Session, deal_closure_set_id: str) -> list[DealArchiveSnapshot]:
    return list(
        session.scalars(
            select(DealArchiveSnapshot)
            .where(DealArchiveSnapshot.deal_closure_set_id == deal_closure_set_id)
            .order_by(DealArchiveSnapshot.created_at.asc(), DealArchiveSnapshot.id.asc())
        )
    )


def _map_outcome_to_closure_code(outcome_code: OutcomeCode | str) -> DealClosureCode:
    outcome_value = str(outcome_code)
    if outcome_value == str(OutcomeCode.WON):
        return DealClosureCode.CLOSED_WON
    if outcome_value in {str(OutcomeCode.LOST), str(OutcomeCode.REJECTED)}:
        return DealClosureCode.CLOSED_LOST
    if outcome_value == str(OutcomeCode.CANCELLED):
        return DealClosureCode.CLOSED_CANCELLED
    return DealClosureCode.CLOSED_NO_RESULT


def build_deal_closure(session: Session, payload: BuildDealClosureRequest) -> DealClosureSet:
    package = load_closure_package(
        session,
        deal_id=payload.deal_id,
        outcome_intake_set_id=payload.outcome_intake_set_id,
        execution_command_set_id=payload.execution_command_set_id,
    )
    closure_set = DealClosureSet(
        deal_closure_set_id=next_deal_closure_set_id(session, DealClosureSet.deal_closure_set_id),
        deal_id=payload.deal_id,
        outcome_intake_set_id=package.outcome_set.outcome_intake_set_id,
        execution_command_set_id=package.execution_set.execution_command_set_id,
        closure_status=DealClosureStatus.READY,
    )
    session.add(closure_set)
    session.flush()
    try:
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="deal_closure_built",
            source_module_id="M-046",
            severity=EventSeverity.INFO,
            payload_json={
                "deal_closure_set_id": closure_set.deal_closure_set_id,
                "outcome_intake_set_id": package.outcome_set.outcome_intake_set_id,
                "execution_command_set_id": package.execution_set.execution_command_set_id,
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(closure_set)
    return closure_set


def close_deal(session: Session, payload: CloseDealRequest) -> DealClosureSet:
    closure_set = _get_set(session, payload.deal_closure_set_id)
    existing_records = _get_records(session, closure_set.deal_closure_set_id)
    if existing_records:
        raise ValidationError("Deal closure set is already closed")

    package = load_closure_package(
        session,
        deal_id=closure_set.deal_id,
        outcome_intake_set_id=closure_set.outcome_intake_set_id,
        execution_command_set_id=closure_set.execution_command_set_id,
    )
    if (
        str(package.outcome_record.outcome_code) == str(OutcomeCode.WON)
        and str(package.execution_set.execution_status) != str(ExecutionCommandStatus.COMPLETED)
    ):
        raise ValidationError("Won deals can be closed only after execution is completed")

    closure_code = _map_outcome_to_closure_code(package.outcome_record.outcome_code)
    summary_text = payload.summary_text or (
        f"Deal closed with outcome {package.outcome_record.outcome_code} "
        f"and execution status {package.execution_set.execution_status}."
    )
    closure_record = DealClosureRecord(
        deal_closure_id=next_deal_closure_id(session, DealClosureRecord.deal_closure_id),
        deal_closure_set_id=closure_set.deal_closure_set_id,
        closure_code=closure_code,
        summary_text=summary_text,
        closed_at=payload.closed_at or utcnow(),
    )
    session.add(closure_record)
    session.flush()
    try:
        milestone_set_ids = list(
            session.scalars(
                select(DeliveryMilestoneSet.delivery_milestone_set_id).where(
                    DeliveryMilestoneSet.deal_id == closure_set.deal_id
                )
            )
        )
        fulfillment_set_ids = list(
            session.scalars(
                select(SupplierFulfillmentSet.supplier_fulfillment_set_id).where(
                    SupplierFulfillmentSet.deal_id == closure_set.deal_id
                )
            )
        )
        shipping_set_ids = list(
            session.scalars(
                select(ShippingAcceptanceSet.shipping_acceptance_set_id).where(
                    ShippingAcceptanceSet.deal_id == closure_set.deal_id
                )
            )
        )
        payment_set_ids = list(
            session.scalars(
                select(PaymentCollectionSet.payment_collection_set_id).where(
                    PaymentCollectionSet.deal_id == closure_set.deal_id
                )
            )
        )
        snapshot = DealArchiveSnapshot(
            archive_snapshot_id=next_archive_snapshot_id(session, DealArchiveSnapshot.archive_snapshot_id),
            deal_closure_set_id=closure_set.deal_closure_set_id,
            snapshot_manifest_json={
                "deal_id": closure_set.deal_id,
                "outcome_intake_set_id": closure_set.outcome_intake_set_id,
                "execution_command_set_id": closure_set.execution_command_set_id,
                "deal_closure_id": closure_record.deal_closure_id,
                "closure_code": str(closure_code),
                "outcome_code": str(package.outcome_record.outcome_code),
                "execution_status": str(package.execution_set.execution_status),
                "incident_count": package.incident_count,
                "milestone_set_ids": milestone_set_ids,
                "supplier_fulfillment_set_ids": fulfillment_set_ids,
                "shipping_acceptance_set_ids": shipping_set_ids,
                "payment_collection_set_ids": payment_set_ids,
            },
        )
        session.add(snapshot)
        closure_set.closure_status = DealClosureStatus.CLOSED
        closure_set.updated_at = utcnow()
        session.add(closure_set)
        append_event_record(
            session,
            deal_id=closure_set.deal_id,
            event_code="deal_closed",
            source_module_id="M-046",
            severity=EventSeverity.INFO,
            payload_json={
                "deal_closure_set_id": closure_set.deal_closure_set_id,
                "deal_closure_id": closure_record.deal_closure_id,
                "closure_code": str(closure_code),
            },
        )
        append_event_record(
            session,
            deal_id=closure_set.deal_id,
            event_code="deal_archive_snapshot_created",
            source_module_id="M-046",
            severity=EventSeverity.INFO,
            payload_json={
                "deal_closure_set_id": closure_set.deal_closure_set_id,
                "archive_snapshot_id": snapshot.archive_snapshot_id,
            },
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        closure_set = _get_set(session, payload.deal_closure_set_id)
        closure_set.closure_status = DealClosureStatus.FAILED
        closure_set.updated_at = utcnow()
        session.add(closure_set)
        append_event_record(
            session,
            deal_id=closure_set.deal_id,
            event_code="deal_closure_failed",
            source_module_id="M-046",
            severity=EventSeverity.HIGH,
            payload_json={"deal_closure_set_id": closure_set.deal_closure_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(closure_set)
    return closure_set


def get_deal_closure_set(
    session: Session,
    deal_closure_set_id: str,
) -> tuple[DealClosureSet, list[DealClosureRecord], list[DealArchiveSnapshot]]:
    closure_set = _get_set(session, deal_closure_set_id)
    return closure_set, _get_records(session, deal_closure_set_id), _get_snapshots(session, deal_closure_set_id)


def list_deal_closure_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[DealClosureSet, list[DealClosureRecord], list[DealArchiveSnapshot]]]:
    query = select(DealClosureSet).order_by(DealClosureSet.created_at.desc())
    if deal_id:
        query = query.where(DealClosureSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_deal_closure_set(session, item.deal_closure_set_id) for item in sets]


def get_deal_closure_record(session: Session, deal_closure_id: str) -> DealClosureRecord:
    return _get_record(session, deal_closure_id)
