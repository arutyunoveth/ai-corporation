from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.tender_research.repository import TenderRepository


@dataclass(frozen=True)
class LocalSearchDecision:
    status: str
    used_local: bool
    used_sync: bool
    stale: bool


def search_official_44fz(
    session: Session,
    *,
    query: str = "",
    customer_mode: bool = True,
    max_age_seconds: int = 6 * 3600,
    limit: int = 20,
    **filters,
) -> tuple[list, LocalSearchDecision]:
    repo = TenderRepository(session)
    latest = repo.latest_tender_seen_at("eis_getdocs_bulk")
    stale = True
    if latest is not None:
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        stale = (datetime.now(timezone.utc) - latest).total_seconds() > max_age_seconds
    results = repo.search_tenders(query=query, source="eis_getdocs_bulk", limit=limit, **filters)
    if results:
        return results, LocalSearchDecision("ok_stale" if stale else "ok", True, False, stale)
    if customer_mode:
        return [], LocalSearchDecision("search_unavailable", False, False, stale)
    return [], LocalSearchDecision("search_unavailable", False, False, stale)
