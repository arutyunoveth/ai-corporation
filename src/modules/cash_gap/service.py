from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.cash_gap.models import CashGapRecord, CashGapScenario, CashGapSet
from src.modules.cash_gap.schemas import BuildCashGapRequest
from src.modules.cost_model.service import get_cost_model_set
from src.modules.event_log.service import append_event_record
from src.shared.db.base import utcnow
from src.shared.enums import CashGapStatus, EventSeverity
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_cash_gap_id, next_cash_gap_set_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, cash_gap_set_id: str) -> CashGapSet:
    record = session.scalar(select(CashGapSet).where(CashGapSet.cash_gap_set_id == cash_gap_set_id))
    if not record:
        raise NotFoundError(f"Cash gap set '{cash_gap_set_id}' was not found")
    return record


def _get_records(session: Session, cash_gap_set_id: str) -> list[CashGapRecord]:
    return list(
        session.scalars(
            select(CashGapRecord)
            .where(CashGapRecord.cash_gap_set_id == cash_gap_set_id)
            .order_by(CashGapRecord.created_at.asc(), CashGapRecord.id.asc())
        )
    )


def _get_scenarios(session: Session, cash_gap_id: str) -> list[CashGapScenario]:
    return list(
        session.scalars(
            select(CashGapScenario)
            .where(CashGapScenario.cash_gap_id == cash_gap_id)
            .order_by(CashGapScenario.created_at.asc(), CashGapScenario.id.asc())
        )
    )


def build_cash_gap(session: Session, payload: BuildCashGapRequest) -> CashGapSet:
    cost_model_set, records = get_cost_model_set(session, payload.cost_model_set_id)
    require_same_reference(payload.deal_id, cost_model_set.deal_id, "deal_id")
    if not records:
        raise ValidationError("Cash gap requires a built cost model set with records")
    cost_record, _lines = records[0]
    peak_gap_amount = round(cost_record.total_cost * 0.55, 2)
    gap_duration_days = 45 if peak_gap_amount <= 500000 else 60 if peak_gap_amount <= 1500000 else 90
    currency_code = cost_record.currency_code

    cash_gap_set = CashGapSet(
        cash_gap_set_id=next_cash_gap_set_id(session, CashGapSet.cash_gap_set_id),
        deal_id=payload.deal_id,
        cost_model_set_id=cost_model_set.cost_model_set_id,
        cash_gap_status=CashGapStatus.BUILT,
    )
    session.add(cash_gap_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="cash_gap_build_started",
        source_module_id="M-023",
        severity=EventSeverity.INFO,
        payload_json={"cash_gap_set_id": cash_gap_set.cash_gap_set_id, "cost_model_set_id": cost_model_set.cost_model_set_id},
    )
    try:
        record = CashGapRecord(
            cash_gap_id=next_cash_gap_id(session, CashGapRecord.cash_gap_id),
            cash_gap_set_id=cash_gap_set.cash_gap_set_id,
            peak_gap_amount=peak_gap_amount,
            gap_duration_days=gap_duration_days,
            currency_code=currency_code,
            notes="Rule-based cash gap estimation from total cost and assumed payment lag.",
        )
        session.add(record)
        session.flush()
        scenarios = [
            ("BASE", "Base timing", peak_gap_amount, gap_duration_days),
            ("FAST_PAYMENT", "Accelerated customer payment", round(peak_gap_amount * 0.75, 2), max(20, gap_duration_days - 15)),
            ("DELAYED_PAYMENT", "Delayed customer payment", round(peak_gap_amount * 1.25, 2), gap_duration_days + 20),
        ]
        for scenario_code, scenario_name, scenario_gap, scenario_days in scenarios:
            session.add(
                CashGapScenario(
                    cash_gap_id=record.cash_gap_id,
                    scenario_code=scenario_code,
                    scenario_name=scenario_name,
                    peak_gap_amount=scenario_gap,
                    gap_duration_days=scenario_days,
                )
            )
        cash_gap_set.updated_at = utcnow()
        session.add(cash_gap_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="cash_gap_built",
            source_module_id="M-023",
            severity=EventSeverity.INFO,
            payload_json={
                "cash_gap_set_id": cash_gap_set.cash_gap_set_id,
                "cash_gap_id": record.cash_gap_id,
                "peak_gap_amount": peak_gap_amount,
                "gap_duration_days": gap_duration_days,
            },
        )
        session.commit()
    except Exception as exc:
        cash_gap_set.cash_gap_status = CashGapStatus.FAILED
        cash_gap_set.updated_at = utcnow()
        session.add(cash_gap_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="cash_gap_failed",
            source_module_id="M-023",
            severity=EventSeverity.HIGH,
            payload_json={"cash_gap_set_id": cash_gap_set.cash_gap_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(cash_gap_set)
    return cash_gap_set


def get_cash_gap_set(session: Session, cash_gap_set_id: str) -> tuple[CashGapSet, list[tuple[CashGapRecord, list[CashGapScenario]]]]:
    cash_gap_set = _get_set(session, cash_gap_set_id)
    records = _get_records(session, cash_gap_set_id)
    return cash_gap_set, [(record, _get_scenarios(session, record.cash_gap_id)) for record in records]


def list_cash_gap_sets(session: Session, *, deal_id: str | None = None) -> list[tuple[CashGapSet, list[tuple[CashGapRecord, list[CashGapScenario]]]]]:
    query = select(CashGapSet).order_by(CashGapSet.created_at.desc())
    if deal_id:
        query = query.where(CashGapSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_cash_gap_set(session, item.cash_gap_set_id) for item in sets]


def get_cash_gap_record(session: Session, cash_gap_id: str) -> tuple[CashGapRecord, list[CashGapScenario]]:
    record = session.scalar(select(CashGapRecord).where(CashGapRecord.cash_gap_id == cash_gap_id))
    if not record:
        raise NotFoundError(f"Cash gap record '{cash_gap_id}' was not found")
    return record, _get_scenarios(session, cash_gap_id)
