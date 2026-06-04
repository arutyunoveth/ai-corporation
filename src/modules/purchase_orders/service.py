from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.purchase_orders.models import (
    PurchaseOrderItem,
    PurchaseOrderLink,
    PurchaseOrderRecord,
    PurchaseOrderSet,
)
from src.modules.purchase_orders.schemas import BuildPurchaseOrderRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, PurchaseOrderStatus
from src.shared.errors import NotFoundError, ValidationError
from src.shared.execution_entry_package import load_execution_entry_context
from src.shared.ids import next_purchase_order_id, next_purchase_order_set_id


def _get_set(session: Session, purchase_order_set_id: str) -> PurchaseOrderSet:
    record = session.scalar(select(PurchaseOrderSet).where(PurchaseOrderSet.purchase_order_set_id == purchase_order_set_id))
    if not record:
        raise NotFoundError(f"Purchase order set '{purchase_order_set_id}' was not found")
    return record


def _get_record(session: Session, purchase_order_id: str) -> PurchaseOrderRecord:
    record = session.scalar(select(PurchaseOrderRecord).where(PurchaseOrderRecord.purchase_order_id == purchase_order_id))
    if not record:
        raise NotFoundError(f"Purchase order record '{purchase_order_id}' was not found")
    return record


def _get_records(session: Session, purchase_order_set_id: str) -> list[PurchaseOrderRecord]:
    return list(
        session.scalars(
            select(PurchaseOrderRecord)
            .where(PurchaseOrderRecord.purchase_order_set_id == purchase_order_set_id)
            .order_by(PurchaseOrderRecord.created_at.asc(), PurchaseOrderRecord.id.asc())
        )
    )


def _get_items(session: Session, purchase_order_id: str) -> list[PurchaseOrderItem]:
    return list(
        session.scalars(
            select(PurchaseOrderItem)
            .where(PurchaseOrderItem.purchase_order_id == purchase_order_id)
            .order_by(PurchaseOrderItem.created_at.asc(), PurchaseOrderItem.id.asc())
        )
    )


def _get_links(session: Session, purchase_order_id: str) -> list[PurchaseOrderLink]:
    return list(
        session.scalars(
            select(PurchaseOrderLink)
            .where(PurchaseOrderLink.purchase_order_id == purchase_order_id)
            .order_by(PurchaseOrderLink.created_at.asc(), PurchaseOrderLink.id.asc())
        )
    )


def build_purchase_order(session: Session, payload: BuildPurchaseOrderRequest) -> PurchaseOrderSet:
    context = load_execution_entry_context(session, deal_id=payload.deal_id, supplier_id=payload.supplier_id)
    if not context.supplier_profile:
        raise ValidationError(f"Supplier '{payload.supplier_id}' does not exist")
    if not context.supplier_contract_set or not context.supplier_contract_record:
        raise ValidationError("Purchase order requires a canonical supplier contract draft")
    if not context.execution_plan_set or not context.execution_plan_record:
        raise ValidationError("Purchase order requires a canonical execution plan")

    po_set = PurchaseOrderSet(
        purchase_order_set_id=next_purchase_order_set_id(session, PurchaseOrderSet.purchase_order_set_id),
        deal_id=payload.deal_id,
        supplier_id=payload.supplier_id,
        po_status=PurchaseOrderStatus.CREATED,
    )
    session.add(po_set)
    session.flush()
    try:
        po_id = next_purchase_order_id(session, PurchaseOrderRecord.purchase_order_id)
        summary_text = (
            f"Purchase order prepared for supplier {payload.supplier_id} from execution plan "
            f"{context.execution_plan_set.execution_plan_set_id}."
        )
        record = PurchaseOrderRecord(
            purchase_order_id=po_id,
            purchase_order_set_id=po_set.purchase_order_set_id,
            po_number=po_id,
            summary_text=summary_text,
        )
        session.add(record)
        session.flush()

        if context.supplier_contract_obligations:
            for index, obligation in enumerate(context.supplier_contract_obligations, start=1):
                session.add(
                    PurchaseOrderItem(
                        purchase_order_id=record.purchase_order_id,
                        item_code=f"PO-LINE-{index:03d}",
                        item_description=obligation.obligation_text,
                        quantity=1,
                    )
                )
        else:
            session.add(
                PurchaseOrderItem(
                    purchase_order_id=record.purchase_order_id,
                    item_code="PO-LINE-001",
                    item_description="Supplier must fulfill the agreed execution scope.",
                    quantity=1,
                )
            )

        source_refs = [
            context.supplier_contract_set.supplier_contract_set_id,
            context.execution_plan_set.execution_plan_set_id,
        ]
        if context.supplier_quote:
            source_refs.append(context.supplier_quote.quote_id)
        for source_ref in source_refs:
            session.add(
                PurchaseOrderLink(
                    purchase_order_id=record.purchase_order_id,
                    source_ref=source_ref,
                )
            )

        po_set.updated_at = utcnow()
        session.add(po_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="purchase_order_built",
            source_module_id="M-037",
            severity=EventSeverity.INFO,
            payload_json={
                "purchase_order_set_id": po_set.purchase_order_set_id,
                "purchase_order_id": record.purchase_order_id,
                "supplier_id": payload.supplier_id,
            },
        )
        session.commit()
    except Exception as exc:
        po_set.po_status = PurchaseOrderStatus.FAILED
        po_set.updated_at = utcnow()
        session.add(po_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="purchase_order_failed",
            source_module_id="M-037",
            severity=EventSeverity.HIGH,
            payload_json={"purchase_order_set_id": po_set.purchase_order_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(po_set)
    return po_set


def get_purchase_order_set(
    session: Session,
    purchase_order_set_id: str,
) -> tuple[PurchaseOrderSet, list[tuple[PurchaseOrderRecord, list[PurchaseOrderItem], list[PurchaseOrderLink]]]]:
    po_set = _get_set(session, purchase_order_set_id)
    records = _get_records(session, purchase_order_set_id)
    return po_set, [(record, _get_items(session, record.purchase_order_id), _get_links(session, record.purchase_order_id)) for record in records]


def list_purchase_order_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[PurchaseOrderSet, list[tuple[PurchaseOrderRecord, list[PurchaseOrderItem], list[PurchaseOrderLink]]]]]:
    query = select(PurchaseOrderSet).order_by(PurchaseOrderSet.created_at.desc(), PurchaseOrderSet.id.desc())
    if deal_id:
        query = query.where(PurchaseOrderSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_purchase_order_set(session, item.purchase_order_set_id) for item in sets]


def get_purchase_order_record(
    session: Session,
    purchase_order_id: str,
) -> tuple[PurchaseOrderRecord, list[PurchaseOrderItem], list[PurchaseOrderLink]]:
    record = _get_record(session, purchase_order_id)
    return record, _get_items(session, purchase_order_id), _get_links(session, purchase_order_id)
