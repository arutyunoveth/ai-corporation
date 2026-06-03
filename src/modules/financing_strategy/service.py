from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.cash_gap.service import get_cash_gap_set
from src.modules.event_log.service import append_event_record
from src.modules.financing_strategy.models import FinancingStrategyOption, FinancingStrategyRecord, FinancingStrategySet
from src.modules.financing_strategy.schemas import BuildFinancingStrategyRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, FinancingFeasibilityStatus, FinancingStrategyStatus
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_financing_strategy_id, next_financing_strategy_set_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, financing_strategy_set_id: str) -> FinancingStrategySet:
    record = session.scalar(
        select(FinancingStrategySet).where(FinancingStrategySet.financing_strategy_set_id == financing_strategy_set_id)
    )
    if not record:
        raise NotFoundError(f"Financing strategy set '{financing_strategy_set_id}' was not found")
    return record


def _get_records(session: Session, financing_strategy_set_id: str) -> list[FinancingStrategyRecord]:
    return list(
        session.scalars(
            select(FinancingStrategyRecord)
            .where(FinancingStrategyRecord.financing_strategy_set_id == financing_strategy_set_id)
            .order_by(FinancingStrategyRecord.created_at.asc(), FinancingStrategyRecord.id.asc())
        )
    )


def _get_options(session: Session, financing_strategy_id: str) -> list[FinancingStrategyOption]:
    return list(
        session.scalars(
            select(FinancingStrategyOption)
            .where(FinancingStrategyOption.financing_strategy_id == financing_strategy_id)
            .order_by(FinancingStrategyOption.created_at.asc(), FinancingStrategyOption.id.asc())
        )
    )


def build_financing_strategy(session: Session, payload: BuildFinancingStrategyRequest) -> FinancingStrategySet:
    cash_gap_set, records = get_cash_gap_set(session, payload.cash_gap_set_id)
    require_same_reference(payload.deal_id, cash_gap_set.deal_id, "deal_id")
    if not records:
        raise ValidationError("Financing strategy requires a built cash gap set with records")
    cash_gap_record, _scenarios = records[0]
    peak_gap = cash_gap_record.peak_gap_amount
    duration = cash_gap_record.gap_duration_days
    currency_code = cash_gap_record.currency_code

    financing_strategy_set = FinancingStrategySet(
        financing_strategy_set_id=next_financing_strategy_set_id(session, FinancingStrategySet.financing_strategy_set_id),
        deal_id=payload.deal_id,
        cash_gap_set_id=cash_gap_set.cash_gap_set_id,
        strategy_status=FinancingStrategyStatus.BUILT,
    )
    session.add(financing_strategy_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="financing_strategy_build_started",
        source_module_id="M-024",
        severity=EventSeverity.INFO,
        payload_json={"financing_strategy_set_id": financing_strategy_set.financing_strategy_set_id, "cash_gap_set_id": cash_gap_set.cash_gap_set_id},
    )
    try:
        options = [
            {
                "option_code": "SELF_FUNDED",
                "option_name": "Self-funded bridge",
                "funding_amount": peak_gap,
                "funding_cost": round(peak_gap * 0.0, 2),
                "feasibility_status": FinancingFeasibilityStatus.FEASIBLE if peak_gap <= 300000 else FinancingFeasibilityStatus.LIMITED if peak_gap <= 1000000 else FinancingFeasibilityStatus.INFEASIBLE,
            },
            {
                "option_code": "FACTORING",
                "option_name": "Receivables factoring",
                "funding_amount": round(peak_gap * 0.85, 2),
                "funding_cost": round(peak_gap * (0.06 if duration <= 45 else 0.09), 2),
                "feasibility_status": FinancingFeasibilityStatus.FEASIBLE if duration <= 60 else FinancingFeasibilityStatus.LIMITED,
            },
            {
                "option_code": "BANK_LINE",
                "option_name": "Bank credit line",
                "funding_amount": peak_gap,
                "funding_cost": round(peak_gap * (0.08 if duration <= 60 else 0.12), 2),
                "feasibility_status": FinancingFeasibilityStatus.FEASIBLE if peak_gap <= 2000000 else FinancingFeasibilityStatus.LIMITED,
            },
        ]
        ranked_options = sorted(
            options,
            key=lambda item: (
                0 if item["feasibility_status"] == FinancingFeasibilityStatus.FEASIBLE else 1 if item["feasibility_status"] == FinancingFeasibilityStatus.LIMITED else 2,
                item["funding_cost"],
            ),
        )
        recommended = ranked_options[0]
        strategy_record = FinancingStrategyRecord(
            financing_strategy_id=next_financing_strategy_id(session, FinancingStrategyRecord.financing_strategy_id),
            financing_strategy_set_id=financing_strategy_set.financing_strategy_set_id,
            recommended_option_code=recommended["option_code"],
            feasible=recommended["feasibility_status"] != FinancingFeasibilityStatus.INFEASIBLE,
            notes=f"Recommended based on peak gap {peak_gap:.2f} and duration {duration} days.",
        )
        session.add(strategy_record)
        session.flush()
        for option in options:
            session.add(
                FinancingStrategyOption(
                    financing_strategy_id=strategy_record.financing_strategy_id,
                    option_code=option["option_code"],
                    option_name=option["option_name"],
                    funding_amount=option["funding_amount"],
                    funding_cost=option["funding_cost"],
                    currency_code=currency_code,
                    feasibility_status=option["feasibility_status"],
                )
            )
        financing_strategy_set.updated_at = utcnow()
        session.add(financing_strategy_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="financing_strategy_built",
            source_module_id="M-024",
            severity=EventSeverity.INFO,
            payload_json={
                "financing_strategy_set_id": financing_strategy_set.financing_strategy_set_id,
                "financing_strategy_id": strategy_record.financing_strategy_id,
                "recommended_option_code": strategy_record.recommended_option_code,
            },
        )
        session.commit()
    except Exception as exc:
        financing_strategy_set.strategy_status = FinancingStrategyStatus.FAILED
        financing_strategy_set.updated_at = utcnow()
        session.add(financing_strategy_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="financing_strategy_failed",
            source_module_id="M-024",
            severity=EventSeverity.HIGH,
            payload_json={"financing_strategy_set_id": financing_strategy_set.financing_strategy_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(financing_strategy_set)
    return financing_strategy_set


def get_financing_strategy_set(session: Session, financing_strategy_set_id: str) -> tuple[FinancingStrategySet, list[tuple[FinancingStrategyRecord, list[FinancingStrategyOption]]]]:
    financing_strategy_set = _get_set(session, financing_strategy_set_id)
    records = _get_records(session, financing_strategy_set_id)
    return financing_strategy_set, [(record, _get_options(session, record.financing_strategy_id)) for record in records]


def list_financing_strategy_sets(session: Session, *, deal_id: str | None = None) -> list[tuple[FinancingStrategySet, list[tuple[FinancingStrategyRecord, list[FinancingStrategyOption]]]]]:
    query = select(FinancingStrategySet).order_by(FinancingStrategySet.created_at.desc())
    if deal_id:
        query = query.where(FinancingStrategySet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_financing_strategy_set(session, item.financing_strategy_set_id) for item in sets]


def get_financing_strategy_record(session: Session, financing_strategy_id: str) -> tuple[FinancingStrategyRecord, list[FinancingStrategyOption]]:
    record = session.scalar(select(FinancingStrategyRecord).where(FinancingStrategyRecord.financing_strategy_id == financing_strategy_id))
    if not record:
        raise NotFoundError(f"Financing strategy record '{financing_strategy_id}' was not found")
    return record, _get_options(session, financing_strategy_id)
