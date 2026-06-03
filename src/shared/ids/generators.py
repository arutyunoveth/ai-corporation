from datetime import datetime, timezone

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _next_business_id(
    session: Session,
    *,
    prefix: str,
    column: ColumnElement[str],
) -> str:
    year = _current_year()
    base = f"{prefix}-{year}-"
    latest = session.scalar(
        select(column).where(column.like(f"{base}%")).order_by(column.desc()).limit(1)
    )
    if latest:
        sequence = int(str(latest).rsplit("-", maxsplit=1)[1]) + 1
    else:
        sequence = 1
    return f"{base}{sequence:06d}"


def next_deal_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DL", column=column)


def next_artifact_ref(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="ART", column=column)


def next_event_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="EVT", column=column)


def next_decision_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DEC", column=column)


def next_intake_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="INT", column=column)


def next_document_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DS", column=column)


def next_ingestion_run_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DIR", column=column)


def next_tender_summary_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="TS", column=column)


def next_screening_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SCR", column=column)


def next_priority_score_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="PRS", column=column)


def next_compliance_matrix_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="CM", column=column)


def next_document_requirement_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DRS", column=column)


def next_risk_flag_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="IRF", column=column)


def next_supplier_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SUP", column=column)


def next_supplier_shortlist_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SSL", column=column)


def next_rfq_batch_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="RB", column=column)


def next_rfq_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="RFQ", column=column)


def next_supplier_communication_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SCS", column=column)


def next_supplier_thread_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SCT", column=column)


def next_supplier_message_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SM", column=column)


def next_quote_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="QS", column=column)


def next_quote_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="Q", column=column)


def next_supplier_verification_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SVS", column=column)


def next_supplier_verification_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SV", column=column)


def next_quote_comparison_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="QCS", column=column)


def next_cost_model_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="CMS", column=column)


def next_cost_model_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="CMD", column=column)


def next_cash_gap_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="CGS", column=column)


def next_cash_gap_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="CG", column=column)


def next_financing_strategy_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="FSS", column=column)


def next_financing_strategy_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="FS", column=column)


def next_finance_memo_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="FMS", column=column)


def next_finance_memo_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="FM", column=column)


def next_contract_risk_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="CRS", column=column)


def next_contract_risk_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="CR", column=column)


def next_integrated_risk_memo_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="IRMS", column=column)


def next_integrated_risk_memo_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="IRM", column=column)


def next_ceo_approval_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="CAS", column=column)


def next_ceo_approval_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="CA", column=column)


def next_bid_document_collection_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="BDCS", column=column)


def next_bid_package_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="BPS", column=column)


def next_bid_package_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="BP", column=column)


def next_bid_completeness_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="BCS", column=column)


def next_bid_completeness_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="BC", column=column)


def next_submission_readiness_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SRS", column=column)


def next_submission_readiness_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SR", column=column)


def next_submission_execution_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SES", column=column)


def next_submission_execution_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SE", column=column)


def next_submission_attempt_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SA", column=column)


def next_submission_receipt_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SRSR", column=column)


def next_submission_receipt_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SRR", column=column)


def next_post_submission_tracker_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="PSTS", column=column)


def next_post_submission_tracker_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="PST", column=column)


def next_post_submission_event_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="PSE", column=column)


def next_outcome_intake_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="OIS", column=column)


def next_outcome_intake_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="OI", column=column)


def next_delivery_launch_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DLS", column=column)


def next_delivery_launch_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DLC", column=column)


def next_execution_command_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="ECS", column=column)


def next_execution_command_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="EC", column=column)


def next_delivery_milestone_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DMS", column=column)


def next_delivery_milestone_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DM", column=column)


def next_delivery_milestone_event_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DME", column=column)


def next_supplier_fulfillment_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SFS", column=column)


def next_supplier_fulfillment_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SF", column=column)


def next_supplier_fulfillment_event_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SFE", column=column)


def next_shipping_acceptance_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SAS", column=column)


def next_shipping_acceptance_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SHA", column=column)


def next_shipping_acceptance_event_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="SAE", column=column)


def next_payment_collection_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="PCS", column=column)


def next_payment_collection_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="PC", column=column)


def next_payment_collection_event_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="PCE", column=column)


def next_incident_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="INS", column=column)


def next_incident_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="INC", column=column)


def next_escalation_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="ESC", column=column)


def next_deal_closure_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DCS", column=column)


def next_deal_closure_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DC", column=column)


def next_archive_snapshot_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DAS", column=column)


def next_kpi_learning_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="KLS", column=column)


def next_kpi_learning_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="KLR", column=column)


def next_learning_note_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="LN", column=column)


def next_dashboard_snapshot_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DSS", column=column)


def next_dashboard_snapshot_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="DSH", column=column)


def next_archive_export_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="AES", column=column)


def next_archive_export_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="AE", column=column)


def next_learning_automation_set_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="LAS", column=column)


def next_learning_automation_id(session: Session, column: ColumnElement[str]) -> str:
    return _next_business_id(session, prefix="LA", column=column)
