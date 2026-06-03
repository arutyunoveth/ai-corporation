from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.modules.deal_registry.models import Deal
from src.modules.deal_registry.schemas import CreateDealRequest, UpdateDealRequest
from src.modules.event_log.service import append_event_record
from src.modules.status_engine.service import append_initial_status_history
from src.shared.db.base import utcnow
from src.shared.enums import DealStatus, EventSeverity
from src.shared.errors import NotFoundError
from src.shared.ids import next_deal_id
from src.shared.validation import require_non_empty


def _base_query() -> Select[tuple[Deal]]:
    return select(Deal).where(Deal.is_deleted.is_(False))


def create_deal(session: Session, payload: CreateDealRequest) -> Deal:
    require_non_empty(payload.title, "title")
    deal = Deal(
        deal_id=next_deal_id(session, Deal.deal_id),
        title=payload.title.strip(),
        customer_name=payload.customer_name,
        procurement_number=payload.procurement_number,
        procurement_channel=payload.procurement_channel,
        initial_source_type=payload.initial_source_type,
        direction_type=payload.direction_type,
        domain_type=payload.domain_type.strip(),
        current_status=DealStatus.NEW,
    )
    session.add(deal)
    session.flush()
    append_initial_status_history(session, deal_id=deal.deal_id, to_status=DealStatus.NEW)
    append_event_record(
        session,
        deal_id=deal.deal_id,
        event_code="deal_created",
        source_module_id="M-001",
        severity=EventSeverity.INFO,
        payload_json={"title": deal.title},
    )
    session.commit()
    session.refresh(deal)
    return deal


def get_deal(session: Session, deal_id: str) -> Deal:
    deal = session.scalar(_base_query().where(Deal.deal_id == deal_id))
    if not deal:
        raise NotFoundError(f"Deal '{deal_id}' was not found")
    return deal


def list_deals(
    session: Session,
    *,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    procurement_number: str | None = None,
    customer_name: str | None = None,
) -> list[Deal]:
    query = _base_query().order_by(Deal.created_at.desc())
    if status:
        query = query.where(Deal.current_status == status)
    if date_from:
        query = query.where(Deal.created_at >= date_from)
    if date_to:
        query = query.where(Deal.created_at <= date_to)
    if procurement_number:
        query = query.where(Deal.procurement_number == procurement_number)
    if customer_name:
        query = query.where(Deal.customer_name.ilike(f"%{customer_name}%"))
    return list(session.scalars(query))


def update_deal(session: Session, deal_id: str, payload: UpdateDealRequest) -> Deal:
    deal = get_deal(session, deal_id)
    updated_fields: dict[str, str | None] = {}
    for field in ("title", "customer_name", "procurement_number", "procurement_channel", "priority_bucket"):
        value = getattr(payload, field)
        if value is not None:
            setattr(deal, field, value.strip() if isinstance(value, str) else value)
            updated_fields[field] = getattr(deal, field)
    deal.updated_at = utcnow()
    session.add(deal)
    session.flush()
    if updated_fields:
        append_event_record(
            session,
            deal_id=deal.deal_id,
            event_code="deal_metadata_updated",
            source_module_id="M-001",
            severity=EventSeverity.INFO,
            payload_json=updated_fields,
        )
    session.commit()
    session.refresh(deal)
    return deal
