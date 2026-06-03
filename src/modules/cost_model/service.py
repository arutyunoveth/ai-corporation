from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.cost_model.models import CostModelLine, CostModelRecord, CostModelSet
from src.modules.cost_model.schemas import BuildCostModelRequest
from src.modules.event_log.service import append_event_record
from src.modules.quote_comparison.service import get_quote_comparison_set
from src.modules.quote_repository.service import get_quote
from src.shared.db.base import utcnow
from src.shared.enums import CostLineType, CostModelStatus, EventSeverity
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_cost_model_id, next_cost_model_set_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, cost_model_set_id: str) -> CostModelSet:
    record = session.scalar(select(CostModelSet).where(CostModelSet.cost_model_set_id == cost_model_set_id))
    if not record:
        raise NotFoundError(f"Cost model set '{cost_model_set_id}' was not found")
    return record


def _get_records(session: Session, cost_model_set_id: str) -> list[CostModelRecord]:
    return list(
        session.scalars(
            select(CostModelRecord)
            .where(CostModelRecord.cost_model_set_id == cost_model_set_id)
            .order_by(CostModelRecord.created_at.asc(), CostModelRecord.id.asc())
        )
    )


def _get_lines(session: Session, cost_model_id: str) -> list[CostModelLine]:
    return list(
        session.scalars(
            select(CostModelLine)
            .where(CostModelLine.cost_model_id == cost_model_id)
            .order_by(CostModelLine.created_at.asc(), CostModelLine.id.asc())
        )
    )


def build_cost_model(session: Session, payload: BuildCostModelRequest) -> CostModelSet:
    comparison_set, rows, recommendation = get_quote_comparison_set(session, payload.quote_comparison_set_id)
    require_same_reference(payload.deal_id, comparison_set.deal_id, "deal_id")
    if not rows or not recommendation:
        raise ValidationError("Cost model requires a built quote comparison with rows and recommendation")

    quote, _bindings = get_quote(session, recommendation.recommended_quote_id)
    base_quote_total = float(quote.quoted_amount)
    logistics_cost = round(base_quote_total * 0.08, 2)
    top_total_score = rows[0].total_score
    buffer_multiplier = 0.03 if top_total_score >= 85 else 0.05 if top_total_score >= 70 else 0.08
    buffer_cost = round(base_quote_total * buffer_multiplier, 2)
    overhead_cost = round(base_quote_total * 0.07, 2)
    total_cost = round(base_quote_total + logistics_cost + buffer_cost + overhead_cost, 2)
    min_viable_bid = round(total_cost * 1.12, 2)
    currency_code = quote.currency_code

    cost_model_set = CostModelSet(
        cost_model_set_id=next_cost_model_set_id(session, CostModelSet.cost_model_set_id),
        deal_id=payload.deal_id,
        quote_comparison_set_id=comparison_set.quote_comparison_set_id,
        cost_model_status=CostModelStatus.BUILT,
    )
    session.add(cost_model_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="cost_model_build_started",
        source_module_id="M-022",
        severity=EventSeverity.INFO,
        payload_json={"cost_model_set_id": cost_model_set.cost_model_set_id, "quote_comparison_set_id": comparison_set.quote_comparison_set_id},
    )
    try:
        record = CostModelRecord(
            cost_model_id=next_cost_model_id(session, CostModelRecord.cost_model_id),
            cost_model_set_id=cost_model_set.cost_model_set_id,
            base_quote_total=base_quote_total,
            logistics_cost=logistics_cost,
            buffer_cost=buffer_cost,
            overhead_cost=overhead_cost,
            total_cost=total_cost,
            min_viable_bid=min_viable_bid,
            currency_code=currency_code,
        )
        session.add(record)
        session.flush()
        lines = [
            ("LINE-001", CostLineType.BASE_QUOTE, base_quote_total, "Selected recommended quote from comparison"),
            ("LINE-002", CostLineType.LOGISTICS, logistics_cost, "Heuristic logistics allowance at 8% of base quote"),
            ("LINE-003", CostLineType.BUFFER, buffer_cost, "Heuristic execution buffer based on comparison confidence"),
            ("LINE-004", CostLineType.OVERHEAD, overhead_cost, "Heuristic overhead allowance at 7% of base quote"),
        ]
        for line_code, line_type, amount, notes in lines:
            session.add(
                CostModelLine(
                    cost_model_id=record.cost_model_id,
                    line_code=line_code,
                    line_type=line_type,
                    amount=amount,
                    currency_code=currency_code,
                    notes=notes,
                )
            )
        cost_model_set.updated_at = utcnow()
        session.add(cost_model_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="cost_model_built",
            source_module_id="M-022",
            severity=EventSeverity.INFO,
            payload_json={
                "cost_model_set_id": cost_model_set.cost_model_set_id,
                "cost_model_id": record.cost_model_id,
                "total_cost": total_cost,
                "min_viable_bid": min_viable_bid,
            },
        )
        session.commit()
    except Exception as exc:
        cost_model_set.cost_model_status = CostModelStatus.FAILED
        cost_model_set.updated_at = utcnow()
        session.add(cost_model_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="cost_model_failed",
            source_module_id="M-022",
            severity=EventSeverity.HIGH,
            payload_json={"cost_model_set_id": cost_model_set.cost_model_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(cost_model_set)
    return cost_model_set


def get_cost_model_set(session: Session, cost_model_set_id: str) -> tuple[CostModelSet, list[tuple[CostModelRecord, list[CostModelLine]]]]:
    cost_model_set = _get_set(session, cost_model_set_id)
    records = _get_records(session, cost_model_set_id)
    return cost_model_set, [(record, _get_lines(session, record.cost_model_id)) for record in records]


def list_cost_model_sets(session: Session, *, deal_id: str | None = None) -> list[tuple[CostModelSet, list[tuple[CostModelRecord, list[CostModelLine]]]]]:
    query = select(CostModelSet).order_by(CostModelSet.created_at.desc())
    if deal_id:
        query = query.where(CostModelSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_cost_model_set(session, item.cost_model_set_id) for item in sets]


def get_cost_model_record(session: Session, cost_model_id: str) -> tuple[CostModelRecord, list[CostModelLine]]:
    record = session.scalar(select(CostModelRecord).where(CostModelRecord.cost_model_id == cost_model_id))
    if not record:
        raise NotFoundError(f"Cost model record '{cost_model_id}' was not found")
    return record, _get_lines(session, cost_model_id)
