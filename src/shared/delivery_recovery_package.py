from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.modules.incidents.models import EscalationRecord, IncidentRecord, IncidentSet
from src.modules.payment_collection.models import (
    PaymentCollectionEvent,
    PaymentCollectionRecord,
    PaymentCollectionSet,
)
from src.modules.shipping_acceptance.models import (
    ShippingAcceptanceEvent,
    ShippingAcceptanceRecord,
    ShippingAcceptanceSet,
)
from src.modules.supplier_progress.models import (
    SupplierProgressAlert,
    SupplierProgressEvent,
    SupplierProgressRecord,
    SupplierProgressSet,
)
from src.shared.execution_entry_package import ExecutionEntryContext, load_execution_entry_context


def _latest_by_deal(model: type, deal_id: str) -> Select:
    return select(model).where(model.deal_id == deal_id).order_by(model.created_at.desc(), model.id.desc())  # type: ignore[attr-defined]


@dataclass(slots=True)
class DeliveryHelperContext:
    execution_entry: ExecutionEntryContext
    supplier_progress_set: SupplierProgressSet | None
    supplier_progress_record: SupplierProgressRecord | None
    supplier_progress_events: list[SupplierProgressEvent]
    supplier_progress_alerts: list[SupplierProgressAlert]
    shipping_set: ShippingAcceptanceSet | None
    shipping_record: ShippingAcceptanceRecord | None
    shipping_events: list[ShippingAcceptanceEvent]
    incident_set: IncidentSet | None
    incident_records: list[IncidentRecord]
    incident_escalations: list[EscalationRecord]
    payment_set: PaymentCollectionSet | None
    payment_record: PaymentCollectionRecord | None
    payment_events: list[PaymentCollectionEvent]


def load_delivery_helper_context(session: Session, deal_id: str) -> DeliveryHelperContext:
    supplier_progress_set = session.scalar(_latest_by_deal(SupplierProgressSet, deal_id))
    supplier_progress_record = None
    supplier_progress_events: list[SupplierProgressEvent] = []
    supplier_progress_alerts: list[SupplierProgressAlert] = []
    if supplier_progress_set:
        supplier_progress_record = session.scalar(
            select(SupplierProgressRecord)
            .where(SupplierProgressRecord.supplier_progress_set_id == supplier_progress_set.supplier_progress_set_id)
            .order_by(SupplierProgressRecord.created_at.desc(), SupplierProgressRecord.id.desc())
        )
        if supplier_progress_record:
            supplier_progress_events = list(
                session.scalars(
                    select(SupplierProgressEvent)
                    .where(SupplierProgressEvent.supplier_progress_id == supplier_progress_record.supplier_progress_id)
                    .order_by(SupplierProgressEvent.event_timestamp.asc(), SupplierProgressEvent.id.asc())
                )
            )
            supplier_progress_alerts = list(
                session.scalars(
                    select(SupplierProgressAlert)
                    .where(SupplierProgressAlert.supplier_progress_id == supplier_progress_record.supplier_progress_id)
                    .order_by(SupplierProgressAlert.created_at.asc(), SupplierProgressAlert.id.asc())
                )
            )

    shipping_set = session.scalar(_latest_by_deal(ShippingAcceptanceSet, deal_id))
    shipping_record = None
    shipping_events: list[ShippingAcceptanceEvent] = []
    if shipping_set:
        shipping_record = session.scalar(
            select(ShippingAcceptanceRecord)
            .where(ShippingAcceptanceRecord.shipping_acceptance_set_id == shipping_set.shipping_acceptance_set_id)
            .order_by(ShippingAcceptanceRecord.created_at.desc(), ShippingAcceptanceRecord.id.desc())
        )
        if shipping_record:
            shipping_events = list(
                session.scalars(
                    select(ShippingAcceptanceEvent)
                    .where(ShippingAcceptanceEvent.shipping_acceptance_id == shipping_record.shipping_acceptance_id)
                    .order_by(ShippingAcceptanceEvent.event_timestamp.asc(), ShippingAcceptanceEvent.id.asc())
                )
            )

    incident_set = session.scalar(_latest_by_deal(IncidentSet, deal_id))
    incident_records: list[IncidentRecord] = []
    incident_escalations: list[EscalationRecord] = []
    if incident_set:
        incident_records = list(
            session.scalars(
                select(IncidentRecord)
                .where(IncidentRecord.incident_set_id == incident_set.incident_set_id)
                .order_by(IncidentRecord.created_at.asc(), IncidentRecord.id.asc())
            )
        )
        if incident_records:
            incident_ids = [record.incident_id for record in incident_records]
            incident_escalations = list(
                session.scalars(
                    select(EscalationRecord)
                    .where(EscalationRecord.incident_id.in_(incident_ids))
                    .order_by(EscalationRecord.created_at.asc(), EscalationRecord.id.asc())
                )
            )

    payment_set = session.scalar(_latest_by_deal(PaymentCollectionSet, deal_id))
    payment_record = None
    payment_events: list[PaymentCollectionEvent] = []
    if payment_set:
        payment_record = session.scalar(
            select(PaymentCollectionRecord)
            .where(PaymentCollectionRecord.payment_collection_set_id == payment_set.payment_collection_set_id)
            .order_by(PaymentCollectionRecord.created_at.desc(), PaymentCollectionRecord.id.desc())
        )
        if payment_record:
            payment_events = list(
                session.scalars(
                    select(PaymentCollectionEvent)
                    .where(PaymentCollectionEvent.payment_collection_id == payment_record.payment_collection_id)
                    .order_by(PaymentCollectionEvent.event_timestamp.asc(), PaymentCollectionEvent.id.asc())
                )
            )

    return DeliveryHelperContext(
        execution_entry=load_execution_entry_context(session, deal_id=deal_id),
        supplier_progress_set=supplier_progress_set,
        supplier_progress_record=supplier_progress_record,
        supplier_progress_events=supplier_progress_events,
        supplier_progress_alerts=supplier_progress_alerts,
        shipping_set=shipping_set,
        shipping_record=shipping_record,
        shipping_events=shipping_events,
        incident_set=incident_set,
        incident_records=incident_records,
        incident_escalations=incident_escalations,
        payment_set=payment_set,
        payment_record=payment_record,
        payment_events=payment_events,
    )
