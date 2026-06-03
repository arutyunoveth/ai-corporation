from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.finance_memo.models import FinanceMemoFlag, FinanceMemoRecord, FinanceMemoSet
from src.modules.finance_memo.schemas import BuildFinanceMemoRequest
from src.shared.db.base import utcnow
from src.shared.economics_package import load_economics_package
from src.shared.enums import EventSeverity, FinanceMemoStatus, FinanceRecommendation, VerificationFlagSeverity
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_finance_memo_id, next_finance_memo_set_id


def _get_set(session: Session, finance_memo_set_id: str) -> FinanceMemoSet:
    record = session.scalar(select(FinanceMemoSet).where(FinanceMemoSet.finance_memo_set_id == finance_memo_set_id))
    if not record:
        raise NotFoundError(f"Finance memo set '{finance_memo_set_id}' was not found")
    return record


def _get_records(session: Session, finance_memo_set_id: str) -> list[FinanceMemoRecord]:
    return list(
        session.scalars(
            select(FinanceMemoRecord)
            .where(FinanceMemoRecord.finance_memo_set_id == finance_memo_set_id)
            .order_by(FinanceMemoRecord.created_at.asc(), FinanceMemoRecord.id.asc())
        )
    )


def _get_flags(session: Session, finance_memo_id: str) -> list[FinanceMemoFlag]:
    return list(
        session.scalars(
            select(FinanceMemoFlag)
            .where(FinanceMemoFlag.finance_memo_id == finance_memo_id)
            .order_by(FinanceMemoFlag.created_at.asc(), FinanceMemoFlag.id.asc())
        )
    )


def build_finance_memo(session: Session, payload: BuildFinanceMemoRequest) -> FinanceMemoSet:
    package = load_economics_package(
        session,
        deal_id=payload.deal_id,
        cost_model_set_id=payload.cost_model_set_id,
        cash_gap_set_id=payload.cash_gap_set_id,
        financing_strategy_set_id=payload.financing_strategy_set_id,
    )
    if not package.cost_model_records or not package.cash_gap_records or not package.financing_strategy_records:
        raise ValidationError("Finance memo requires formal cost model, cash gap, and financing strategy records")

    cost_record, _cost_lines = package.cost_model_records[0]
    cash_gap_record, _cash_gap_scenarios = package.cash_gap_records[0]
    strategy_record, strategy_options = package.financing_strategy_records[0]
    finance_memo_set = FinanceMemoSet(
        finance_memo_set_id=next_finance_memo_set_id(session, FinanceMemoSet.finance_memo_set_id),
        deal_id=payload.deal_id,
        cost_model_set_id=payload.cost_model_set_id,
        cash_gap_set_id=payload.cash_gap_set_id,
        financing_strategy_set_id=payload.financing_strategy_set_id,
        memo_status=FinanceMemoStatus.BUILT,
    )
    session.add(finance_memo_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="finance_memo_build_started",
        source_module_id="M-025",
        severity=EventSeverity.INFO,
        payload_json={"finance_memo_set_id": finance_memo_set.finance_memo_set_id},
    )
    try:
        flags: list[dict] = []
        margin = round(cost_record.min_viable_bid - cost_record.total_cost, 2)
        if cash_gap_record.peak_gap_amount > 1000000:
            flags.append(
                {
                    "flag_code": "HIGH_CASH_GAP",
                    "severity": VerificationFlagSeverity.HIGH,
                    "summary": "Peak cash gap exceeds the current comfort threshold.",
                }
            )
        if cash_gap_record.gap_duration_days > 60:
            flags.append(
                {
                    "flag_code": "LONG_GAP_DURATION",
                    "severity": VerificationFlagSeverity.MEDIUM,
                    "summary": "Cash gap duration is extended and increases financing pressure.",
                }
            )
        if not strategy_record.feasible:
            flags.append(
                {
                    "flag_code": "NO_FEASIBLE_FINANCING",
                    "severity": VerificationFlagSeverity.CRITICAL,
                    "summary": "No feasible financing path is available under current assumptions.",
                }
            )
        elif any(option.feasibility_status == "LIMITED" for option in strategy_options):
            flags.append(
                {
                    "flag_code": "LIMITED_FINANCING_OPTIONS",
                    "severity": VerificationFlagSeverity.MEDIUM,
                    "summary": "Financing options exist but at least one core path is limited.",
                }
            )

        if not strategy_record.feasible:
            recommendation = FinanceRecommendation.NO_GO
        elif cash_gap_record.peak_gap_amount > 1500000:
            recommendation = FinanceRecommendation.NEEDS_REVIEW
        elif cash_gap_record.peak_gap_amount > 700000 or cash_gap_record.gap_duration_days > 60:
            recommendation = FinanceRecommendation.GO_WITH_CONDITIONS
        else:
            recommendation = FinanceRecommendation.GO

        structured_summary = {
            "total_cost": cost_record.total_cost,
            "min_viable_bid": cost_record.min_viable_bid,
            "currency_code": cost_record.currency_code,
            "peak_cash_gap_amount": cash_gap_record.peak_gap_amount,
            "cash_gap_duration_days": cash_gap_record.gap_duration_days,
            "recommended_financing_option": strategy_record.recommended_option_code,
            "feasible_financing": strategy_record.feasible,
            "margin_buffer": margin,
            "memo_version": "1.0",
        }
        summary_text = (
            f"Total cost baseline: {cost_record.total_cost:.2f} {cost_record.currency_code}. "
            f"Minimum viable bid: {cost_record.min_viable_bid:.2f} {cost_record.currency_code}. "
            f"Peak cash gap: {cash_gap_record.peak_gap_amount:.2f} {cash_gap_record.currency_code} "
            f"for {cash_gap_record.gap_duration_days} days. "
            f"Recommended financing option: {strategy_record.recommended_option_code}. "
            f"Finance recommendation: {recommendation}."
        )

        memo_record = FinanceMemoRecord(
            finance_memo_id=next_finance_memo_id(session, FinanceMemoRecord.finance_memo_id),
            finance_memo_set_id=finance_memo_set.finance_memo_set_id,
            summary_text=summary_text,
            structured_summary_json=structured_summary,
            recommendation=recommendation,
        )
        session.add(memo_record)
        session.flush()
        for flag in flags:
            session.add(FinanceMemoFlag(finance_memo_id=memo_record.finance_memo_id, **flag))
        finance_memo_set.updated_at = utcnow()
        session.add(finance_memo_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="finance_memo_built",
            source_module_id="M-025",
            severity=EventSeverity.INFO,
            payload_json={
                "finance_memo_set_id": finance_memo_set.finance_memo_set_id,
                "finance_memo_id": memo_record.finance_memo_id,
                "recommendation": str(recommendation),
            },
        )
        session.commit()
    except Exception as exc:
        finance_memo_set.memo_status = FinanceMemoStatus.FAILED
        finance_memo_set.updated_at = utcnow()
        session.add(finance_memo_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="finance_memo_failed",
            source_module_id="M-025",
            severity=EventSeverity.HIGH,
            payload_json={"finance_memo_set_id": finance_memo_set.finance_memo_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(finance_memo_set)
    return finance_memo_set


def get_finance_memo_set(session: Session, finance_memo_set_id: str) -> tuple[FinanceMemoSet, list[tuple[FinanceMemoRecord, list[FinanceMemoFlag]]]]:
    finance_memo_set = _get_set(session, finance_memo_set_id)
    records = _get_records(session, finance_memo_set_id)
    return finance_memo_set, [(record, _get_flags(session, record.finance_memo_id)) for record in records]


def list_finance_memo_sets(session: Session, *, deal_id: str | None = None) -> list[tuple[FinanceMemoSet, list[tuple[FinanceMemoRecord, list[FinanceMemoFlag]]]]]:
    query = select(FinanceMemoSet).order_by(FinanceMemoSet.created_at.desc())
    if deal_id:
        query = query.where(FinanceMemoSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_finance_memo_set(session, item.finance_memo_set_id) for item in sets]


def get_finance_memo_record(session: Session, finance_memo_id: str) -> tuple[FinanceMemoRecord, list[FinanceMemoFlag]]:
    record = session.scalar(select(FinanceMemoRecord).where(FinanceMemoRecord.finance_memo_id == finance_memo_id))
    if not record:
        raise NotFoundError(f"Finance memo record '{finance_memo_id}' was not found")
    return record, _get_flags(session, finance_memo_id)
