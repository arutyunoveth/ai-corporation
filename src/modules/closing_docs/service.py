import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.acceptance_control.models import AcceptanceControlSet
from src.modules.closing_docs.models import (
    ClosingDocsFlag,
    ClosingDocsItem,
    ClosingDocsRecord,
    ClosingDocsSet,
)
from src.modules.closing_docs.schemas import BuildClosingDocsRequest
from src.modules.event_log.service import append_event_record
from src.shared.db.base import utcnow
from src.shared.delivery_recovery_package import load_delivery_helper_context
from src.shared.enums import (
    AcceptanceStatus,
    ClosingDocItemStatus,
    ClosingDocsStatus,
    EventSeverity,
    RiskSeverity,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_closing_docs_id, next_closing_docs_set_id


def _get_set(session: Session, closing_docs_set_id: str) -> ClosingDocsSet:
    record = session.scalar(select(ClosingDocsSet).where(ClosingDocsSet.closing_docs_set_id == closing_docs_set_id))
    if not record:
        raise NotFoundError(f"Closing docs set '{closing_docs_set_id}' was not found")
    return record


def _get_record(session: Session, closing_docs_id: str) -> ClosingDocsRecord:
    record = session.scalar(select(ClosingDocsRecord).where(ClosingDocsRecord.closing_docs_id == closing_docs_id))
    if not record:
        raise NotFoundError(f"Closing docs record '{closing_docs_id}' was not found")
    return record


def _get_records(session: Session, closing_docs_set_id: str) -> list[ClosingDocsRecord]:
    return list(
        session.scalars(
            select(ClosingDocsRecord)
            .where(ClosingDocsRecord.closing_docs_set_id == closing_docs_set_id)
            .order_by(ClosingDocsRecord.created_at.asc(), ClosingDocsRecord.id.asc())
        )
    )


def _get_items(session: Session, closing_docs_id: str) -> list[ClosingDocsItem]:
    return list(
        session.scalars(
            select(ClosingDocsItem)
            .where(ClosingDocsItem.closing_docs_id == closing_docs_id)
            .order_by(ClosingDocsItem.created_at.asc(), ClosingDocsItem.id.asc())
        )
    )


def _get_flags(session: Session, closing_docs_id: str) -> list[ClosingDocsFlag]:
    return list(
        session.scalars(
            select(ClosingDocsFlag)
            .where(ClosingDocsFlag.closing_docs_id == closing_docs_id)
            .order_by(ClosingDocsFlag.created_at.asc(), ClosingDocsFlag.id.asc())
        )
    )


def _latest_acceptance_set(session: Session, deal_id: str) -> AcceptanceControlSet | None:
    return session.scalar(
        select(AcceptanceControlSet)
        .where(AcceptanceControlSet.deal_id == deal_id)
        .order_by(AcceptanceControlSet.created_at.desc(), AcceptanceControlSet.id.desc())
    )


def build_closing_docs(session: Session, payload: BuildClosingDocsRequest) -> ClosingDocsSet:
    acceptance_set = _latest_acceptance_set(session, payload.deal_id)
    if not acceptance_set:
        raise ValidationError("Closing docs pack requires canonical acceptance control")

    helper_context = load_delivery_helper_context(session, payload.deal_id)
    docs_status = ClosingDocsStatus.COLLECTING
    if acceptance_set.acceptance_status == AcceptanceStatus.ACCEPTED:
        docs_status = ClosingDocsStatus.READY
    elif acceptance_set.acceptance_status in {AcceptanceStatus.REJECTED, AcceptanceStatus.NEEDS_REVIEW}:
        docs_status = ClosingDocsStatus.PARTIAL

    docs_set = ClosingDocsSet(
        closing_docs_set_id=next_closing_docs_set_id(session, ClosingDocsSet.closing_docs_set_id),
        deal_id=payload.deal_id,
        docs_status=docs_status,
    )
    session.add(docs_set)
    session.flush()
    try:
        manifest = {
            "acceptance_status": acceptance_set.acceptance_status,
            "shipment_ref": helper_context.shipping_record.shipment_ref if helper_context.shipping_record else None,
            "acceptance_ref": helper_context.shipping_record.acceptance_ref if helper_context.shipping_record else None,
        }
        record = ClosingDocsRecord(
            closing_docs_id=next_closing_docs_id(session, ClosingDocsRecord.closing_docs_id),
            closing_docs_set_id=docs_set.closing_docs_set_id,
            docs_manifest_json=json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            summary_text="Canonical closing docs pack assembled from acceptance and delivery context.",
        )
        session.add(record)
        session.flush()
        items = [
            ("CLOSING_ACCEPTANCE_ACT", helper_context.shipping_record.acceptance_ref if helper_context.shipping_record else None),
            ("CLOSING_SHIPMENT_REF", helper_context.shipping_record.shipment_ref if helper_context.shipping_record else None),
            ("CLOSING_PO_REF", helper_context.execution_entry.purchase_order_set.purchase_order_set_id if helper_context.execution_entry.purchase_order_set else None),
            ("CLOSING_SUPPLIER_PROGRESS", helper_context.supplier_progress_set.supplier_progress_set_id if helper_context.supplier_progress_set else None),
        ]
        for item_code, artifact_ref in items:
            status = ClosingDocItemStatus.PRESENT if artifact_ref else ClosingDocItemStatus.MISSING
            session.add(
                ClosingDocsItem(
                    closing_docs_id=record.closing_docs_id,
                    item_code=item_code,
                    artifact_ref=artifact_ref,
                    item_status=status,
                )
            )
            if not artifact_ref:
                session.add(
                    ClosingDocsFlag(
                        closing_docs_id=record.closing_docs_id,
                        flag_code=f"MISSING_{item_code}",
                        severity=RiskSeverity.MEDIUM,
                        summary=f"Missing closing doc source for {item_code}.",
                    )
                )
        if docs_status == ClosingDocsStatus.READY:
            session.add(
                ClosingDocsFlag(
                    closing_docs_id=record.closing_docs_id,
                    flag_code="DOCS_READY_FOR_INVOICE",
                    severity=RiskSeverity.LOW,
                    summary="Closing docs pack is ready for invoicing workflow.",
                )
            )
        docs_set.updated_at = utcnow()
        session.add(docs_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="closing_docs_built",
            source_module_id="M-042",
            severity=EventSeverity.INFO,
            payload_json={
                "closing_docs_set_id": docs_set.closing_docs_set_id,
                "closing_docs_id": record.closing_docs_id,
            },
        )
        session.commit()
    except Exception as exc:
        docs_set.docs_status = ClosingDocsStatus.FAILED
        docs_set.updated_at = utcnow()
        session.add(docs_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="closing_docs_failed",
            source_module_id="M-042",
            severity=EventSeverity.HIGH,
            payload_json={"closing_docs_set_id": docs_set.closing_docs_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(docs_set)
    return docs_set


def get_closing_docs_set(
    session: Session,
    closing_docs_set_id: str,
) -> tuple[ClosingDocsSet, list[tuple[ClosingDocsRecord, list[ClosingDocsItem], list[ClosingDocsFlag]]]]:
    docs_set = _get_set(session, closing_docs_set_id)
    records = _get_records(session, closing_docs_set_id)
    return docs_set, [(record, _get_items(session, record.closing_docs_id), _get_flags(session, record.closing_docs_id)) for record in records]


def list_closing_docs_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[ClosingDocsSet, list[tuple[ClosingDocsRecord, list[ClosingDocsItem], list[ClosingDocsFlag]]]]]:
    query = select(ClosingDocsSet).order_by(ClosingDocsSet.created_at.desc(), ClosingDocsSet.id.desc())
    if deal_id:
        query = query.where(ClosingDocsSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_closing_docs_set(session, item.closing_docs_set_id) for item in sets]


def get_closing_docs_record(
    session: Session,
    closing_docs_id: str,
) -> tuple[ClosingDocsRecord, list[ClosingDocsItem], list[ClosingDocsFlag]]:
    record = _get_record(session, closing_docs_id)
    return record, _get_items(session, closing_docs_id), _get_flags(session, closing_docs_id)
