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

