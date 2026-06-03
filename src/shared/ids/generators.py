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
