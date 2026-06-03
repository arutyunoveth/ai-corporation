from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.contract_risks.service import get_contract_risk_set
from src.modules.event_log.service import append_event_record
from src.modules.finance_memo.service import get_finance_memo_set
from src.modules.initial_tech_risks.service import get_initial_tech_risk_set
from src.modules.integrated_risk_memo.models import (
    IntegratedRiskItem,
    IntegratedRiskMemoRecord,
    IntegratedRiskMemoSet,
)
from src.modules.integrated_risk_memo.schemas import BuildIntegratedRiskMemoRequest
from src.modules.quote_comparison.service import get_quote_comparison_set
from src.modules.supplier_verification.service import get_supplier_verification_set
from src.shared.db.base import utcnow
from src.shared.enums import (
    ApprovalDecision,
    EventSeverity,
    FinanceRecommendation,
    IntegratedRiskMemoStatus,
    RiskSeverity,
    RiskSourceType,
)
from src.shared.errors import NotFoundError
from src.shared.ids import next_integrated_risk_memo_id, next_integrated_risk_memo_set_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, integrated_risk_memo_set_id: str) -> IntegratedRiskMemoSet:
    record = session.scalar(
        select(IntegratedRiskMemoSet).where(
            IntegratedRiskMemoSet.integrated_risk_memo_set_id == integrated_risk_memo_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Integrated risk memo set '{integrated_risk_memo_set_id}' was not found")
    return record


def _get_records(session: Session, integrated_risk_memo_set_id: str) -> list[IntegratedRiskMemoRecord]:
    return list(
        session.scalars(
            select(IntegratedRiskMemoRecord)
            .where(IntegratedRiskMemoRecord.integrated_risk_memo_set_id == integrated_risk_memo_set_id)
            .order_by(IntegratedRiskMemoRecord.created_at.asc(), IntegratedRiskMemoRecord.id.asc())
        )
    )


def _get_items(session: Session, integrated_risk_memo_id: str) -> list[IntegratedRiskItem]:
    return list(
        session.scalars(
            select(IntegratedRiskItem)
            .where(IntegratedRiskItem.integrated_risk_memo_id == integrated_risk_memo_id)
            .order_by(IntegratedRiskItem.created_at.asc(), IntegratedRiskItem.id.asc())
        )
    )


def _severity_rank(severity: str) -> int:
    return {
        RiskSeverity.LOW: 1,
        RiskSeverity.MEDIUM: 2,
        RiskSeverity.HIGH: 3,
        RiskSeverity.CRITICAL: 4,
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }[severity]


def _recommendation_from_items(items: list[dict], finance_recommendation: str) -> ApprovalDecision:
    severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for item in items:
        severity_counts[str(item["severity"])] += 1

    if str(finance_recommendation) == str(FinanceRecommendation.NO_GO) or severity_counts["CRITICAL"] > 0:
        return ApprovalDecision.NO_GO
    if str(finance_recommendation) == str(FinanceRecommendation.NEEDS_REVIEW) or severity_counts["HIGH"] >= 3:
        return ApprovalDecision.NEEDS_REVIEW
    if (
        str(finance_recommendation) == str(FinanceRecommendation.GO_WITH_CONDITIONS)
        or severity_counts["HIGH"] >= 1
        or severity_counts["MEDIUM"] >= 3
    ):
        return ApprovalDecision.GO_WITH_CONDITIONS
    return ApprovalDecision.GO


def _build_risk_items(
    tech_flags,
    supplier_records,
    comparison_rows,
    comparison_recommendation,
    finance_record,
    finance_flags,
    contract_records,
) -> list[dict]:
    items: list[dict] = []

    for flag in tech_flags:
        items.append(
            {
                "risk_source_type": RiskSourceType.TECH,
                "source_object_ref": f"TECH:{flag.risk_flag_set_id}:{flag.row_code}",
                "severity": flag.severity,
                "summary": flag.summary,
                "mitigation_hint": flag.mitigation_hint,
            }
        )

    for record, flags in supplier_records:
        for flag in flags:
            items.append(
                {
                    "risk_source_type": RiskSourceType.SUPPLIER,
                    "source_object_ref": f"SUPPLIER_VERIFICATION:{record.supplier_verification_id}:{flag.flag_code}",
                    "severity": flag.severity,
                    "summary": flag.summary,
                    "mitigation_hint": record.notes,
                }
            )

    if comparison_rows:
        top_row = comparison_rows[0]
        if top_row.quality_score < 70:
            items.append(
                {
                    "risk_source_type": RiskSourceType.QUOTE,
                    "source_object_ref": f"QUOTE_COMPARISON:{top_row.quote_comparison_set_id}:{top_row.quote_id}",
                    "severity": RiskSeverity.HIGH,
                    "summary": "Recommended quote has weak quality confidence relative to the current threshold.",
                    "mitigation_hint": top_row.comparison_notes,
                }
            )
        elif top_row.total_score < 80:
            items.append(
                {
                    "risk_source_type": RiskSourceType.QUOTE,
                    "source_object_ref": f"QUOTE_COMPARISON:{top_row.quote_comparison_set_id}:{top_row.quote_id}",
                    "severity": RiskSeverity.MEDIUM,
                    "summary": "Recommended quote is acceptable but not strongly separated from fallback options.",
                    "mitigation_hint": top_row.comparison_notes,
                }
            )
        if len(comparison_rows) > 1 and (comparison_rows[0].total_score - comparison_rows[1].total_score) < 5:
            items.append(
                {
                    "risk_source_type": RiskSourceType.QUOTE,
                    "source_object_ref": f"QUOTE_COMPARISON:{comparison_rows[0].quote_comparison_set_id}",
                    "severity": RiskSeverity.LOW,
                    "summary": "Quote ranking spread is narrow; a fallback option should remain available.",
                    "mitigation_hint": comparison_recommendation.rationale if comparison_recommendation else None,
                }
            )

    for flag in finance_flags:
        items.append(
            {
                "risk_source_type": RiskSourceType.FINANCE,
                "source_object_ref": f"FINANCE_MEMO:{finance_record.finance_memo_id}:{flag.flag_code}",
                "severity": flag.severity,
                "summary": flag.summary,
                "mitigation_hint": finance_record.summary_text,
            }
        )
    if not finance_flags and str(finance_record.recommendation) != str(FinanceRecommendation.GO):
        items.append(
            {
                "risk_source_type": RiskSourceType.FINANCE,
                "source_object_ref": f"FINANCE_MEMO:{finance_record.finance_memo_id}",
                "severity": RiskSeverity.MEDIUM,
                "summary": "Finance memo recommendation is not a clean GO and needs explicit approval attention.",
                "mitigation_hint": finance_record.summary_text,
            }
        )

    for record, flags in contract_records:
        if flags:
            for flag in flags:
                items.append(
                    {
                        "risk_source_type": RiskSourceType.CONTRACT,
                        "source_object_ref": f"CONTRACT_RISK:{record.contract_risk_id}:{flag.flag_code}",
                        "severity": flag.severity,
                        "summary": flag.summary,
                        "mitigation_hint": record.notes,
                    }
                )
        else:
            items.append(
                {
                    "risk_source_type": RiskSourceType.CONTRACT,
                    "source_object_ref": f"CONTRACT_RISK:{record.contract_risk_id}",
                    "severity": record.severity,
                    "summary": record.summary,
                    "mitigation_hint": record.notes,
                }
            )

    items.sort(key=lambda item: (-_severity_rank(str(item["severity"])), str(item["risk_source_type"])))
    return items


def build_integrated_risk_memo(
    session: Session,
    payload: BuildIntegratedRiskMemoRequest,
) -> IntegratedRiskMemoSet:
    tech_set, tech_flags = get_initial_tech_risk_set(session, payload.initial_tech_risk_flag_set_id)
    supplier_set, supplier_records = get_supplier_verification_set(session, payload.supplier_verification_set_id)
    comparison_set, comparison_rows, comparison_recommendation = get_quote_comparison_set(session, payload.quote_comparison_set_id)
    finance_set, finance_records = get_finance_memo_set(session, payload.finance_memo_set_id)
    contract_set, contract_records = get_contract_risk_set(session, payload.contract_risk_set_id)

    for actual_deal_id in (
        tech_set.deal_id,
        supplier_set.deal_id,
        comparison_set.deal_id,
        finance_set.deal_id,
        contract_set.deal_id,
    ):
        require_same_reference(payload.deal_id, actual_deal_id, "deal_id")

    if not finance_records:
        raise NotFoundError("Finance memo set does not contain persisted finance memo records")
    finance_record, finance_flags = finance_records[0]
    memo_set = IntegratedRiskMemoSet(
        integrated_risk_memo_set_id=next_integrated_risk_memo_set_id(
            session, IntegratedRiskMemoSet.integrated_risk_memo_set_id
        ),
        deal_id=payload.deal_id,
        initial_tech_risk_flag_set_id=tech_set.risk_flag_set_id,
        supplier_verification_set_id=supplier_set.supplier_verification_set_id,
        quote_comparison_set_id=comparison_set.quote_comparison_set_id,
        finance_memo_set_id=finance_set.finance_memo_set_id,
        contract_risk_set_id=contract_set.contract_risk_set_id,
        memo_status=IntegratedRiskMemoStatus.BUILT,
    )
    session.add(memo_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="integrated_risk_memo_build_started",
        source_module_id="M-027",
        severity=EventSeverity.INFO,
        payload_json={"integrated_risk_memo_set_id": memo_set.integrated_risk_memo_set_id},
    )
    try:
        items_data = _build_risk_items(
            tech_flags,
            supplier_records,
            comparison_rows,
            comparison_recommendation,
            finance_record,
            finance_flags,
            contract_records,
        )
        recommendation = _recommendation_from_items(items_data, str(finance_record.recommendation))
        counts_by_source: dict[str, int] = {}
        counts_by_severity: dict[str, int] = {}
        for item in items_data:
            counts_by_source[str(item["risk_source_type"])] = counts_by_source.get(str(item["risk_source_type"]), 0) + 1
            counts_by_severity[str(item["severity"])] = counts_by_severity.get(str(item["severity"]), 0) + 1
        structured_summary = {
            "risk_item_count": len(items_data),
            "counts_by_source": counts_by_source,
            "counts_by_severity": counts_by_severity,
            "finance_recommendation": str(finance_record.recommendation),
            "memo_version": "1.0",
        }
        summary_text = (
            f"Integrated risk memo aggregates {len(items_data)} persisted risk items. "
            f"Highest severity: {max((str(item['severity']) for item in items_data), key=_severity_rank)}. "
            f"System recommendation: {recommendation}."
        )
        record = IntegratedRiskMemoRecord(
            integrated_risk_memo_id=next_integrated_risk_memo_id(
                session, IntegratedRiskMemoRecord.integrated_risk_memo_id
            ),
            integrated_risk_memo_set_id=memo_set.integrated_risk_memo_set_id,
            summary_text=summary_text,
            structured_summary_json=structured_summary,
            recommendation=recommendation,
        )
        session.add(record)
        session.flush()
        for item_data in items_data:
            session.add(IntegratedRiskItem(integrated_risk_memo_id=record.integrated_risk_memo_id, **item_data))
        memo_set.updated_at = utcnow()
        session.add(memo_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="integrated_risk_memo_built",
            source_module_id="M-027",
            severity=EventSeverity.INFO,
            payload_json={
                "integrated_risk_memo_set_id": memo_set.integrated_risk_memo_set_id,
                "integrated_risk_memo_id": record.integrated_risk_memo_id,
                "recommendation": str(recommendation),
            },
        )
        session.commit()
    except Exception as exc:
        memo_set.memo_status = IntegratedRiskMemoStatus.FAILED
        memo_set.updated_at = utcnow()
        session.add(memo_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="integrated_risk_memo_failed",
            source_module_id="M-027",
            severity=EventSeverity.HIGH,
            payload_json={"integrated_risk_memo_set_id": memo_set.integrated_risk_memo_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(memo_set)
    return memo_set


def get_integrated_risk_memo_set(
    session: Session,
    integrated_risk_memo_set_id: str,
) -> tuple[IntegratedRiskMemoSet, list[tuple[IntegratedRiskMemoRecord, list[IntegratedRiskItem]]]]:
    memo_set = _get_set(session, integrated_risk_memo_set_id)
    records = _get_records(session, integrated_risk_memo_set_id)
    return memo_set, [(record, _get_items(session, record.integrated_risk_memo_id)) for record in records]


def list_integrated_risk_memo_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[IntegratedRiskMemoSet, list[tuple[IntegratedRiskMemoRecord, list[IntegratedRiskItem]]]]]:
    query = select(IntegratedRiskMemoSet).order_by(IntegratedRiskMemoSet.created_at.desc())
    if deal_id:
        query = query.where(IntegratedRiskMemoSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_integrated_risk_memo_set(session, item.integrated_risk_memo_set_id) for item in sets]


def get_integrated_risk_memo_record(
    session: Session,
    integrated_risk_memo_id: str,
) -> tuple[IntegratedRiskMemoRecord, list[IntegratedRiskItem]]:
    record = session.scalar(
        select(IntegratedRiskMemoRecord).where(
            IntegratedRiskMemoRecord.integrated_risk_memo_id == integrated_risk_memo_id
        )
    )
    if not record:
        raise NotFoundError(f"Integrated risk memo record '{integrated_risk_memo_id}' was not found")
    return record, _get_items(session, integrated_risk_memo_id)
