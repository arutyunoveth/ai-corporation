from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session

from src.tender_research.repository import TenderRepository
from src.tender_research.sync.eis_document_types import EIS_DOCUMENT_TYPES
from src.tender_research.sync.eis_params import normalize_eis_region_code
from src.tender_research.sync.providers.eis_getdocs_bulk import BulkFetchResult, EisGetDocsBulkProvider


SyncMode = Literal["targeted", "nationwide", "backfill"]
DEFAULT_TARGET_REGIONS = ("77", "78", "50", "63")
ALL_RUSSIAN_REGIONS = tuple(f"{idx:02d}" for idx in range(1, 100) if idx != 0)


@dataclass
class SyncEisBulkFeedResult:
    mode: SyncMode
    dry_run: bool
    results: list[dict] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"mode": self.mode, "dry_run": self.dry_run, "results": self.results, "errors": self.errors}


def default_sync_dates(today: date | None = None) -> list[date]:
    current = today or date.today()
    return [current, current - timedelta(days=1)]


def sync_eis_bulk_feed(
    *,
    session: Session | None = None,
    regions: list[str] | None = None,
    dates: list[date] | None = None,
    document_types: list[str] | None = None,
    concurrency: int = 2,
    max_archives: int | None = None,
    dry_run: bool = False,
    mode: SyncMode = "targeted",
) -> SyncEisBulkFeedResult:
    effective_concurrency = min(max(concurrency, 1), 2)
    selected_regions = _regions_for_mode(mode, regions)
    selected_dates = dates or default_sync_dates()
    selected_types = document_types or [item.document_type for item in EIS_DOCUMENT_TYPES if item.parser_supported]
    result = SyncEisBulkFeedResult(mode=mode, dry_run=dry_run)
    repository = TenderRepository(session) if session is not None else None
    provider = None if dry_run else EisGetDocsBulkProvider(repository=repository)

    for region in selected_regions:
        normalized_region = normalize_eis_region_code(region)
        for source_date in selected_dates:
            for document_type in selected_types:
                payload = {
                    "region": normalized_region,
                    "date": source_date.isoformat(),
                    "subsystem": "PRIZ",
                    "document_type": document_type,
                }
                if dry_run:
                    result.results.append({**payload, "status": "planned"})
                    continue
                sync_run = None
                if repository is not None:
                    sync_run = repository.create_sync_run(
                        {
                            "source": "eis_getdocs_bulk",
                            "status": "running",
                            "mode": mode,
                            "region_code": normalized_region,
                            "source_date": source_date,
                            "document_type": document_type,
                            "started_at": datetime.now(timezone.utc),
                            "created_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc),
                        }
                    )
                try:
                    fetched = provider.fetch_procurements(
                        region_code=normalized_region,
                        exact_date=source_date,
                        subsystem_type="PRIZ",
                        document_type=document_type,
                        max_archives=max_archives,
                    )
                    stats = fetched.to_dict()
                    result.results.append(stats)
                    if repository is not None:
                        if sync_run is not None:
                            repository.finish_sync_run(
                                sync_run.id,
                                status="success" if not fetched.errors else "partial_failure",
                                stats=stats,
                                error_summary="; ".join(item.get("message", "") for item in fetched.errors[-5:]) or None,
                            )
                        repository.upsert_eis_cursor(
                            {
                                "region_code": normalized_region,
                                "subsystem_type": "PRIZ",
                                "document_type": document_type,
                                "last_requested_date": source_date,
                                "last_success_at": datetime.now(timezone.utc),
                                "last_archive_hash": fetched.archive_urls[-1] if fetched.archive_urls else None,
                                "status": "success" if not fetched.errors else "partial_failure",
                                "consecutive_failures": 0,
                                "next_retry_at": None,
                            }
                        )
                except Exception as exc:  # noqa: BLE001
                    result.errors.append({**payload, "error": str(exc)})
                    if repository is not None:
                        if sync_run is not None:
                            repository.finish_sync_run(sync_run.id, status="failed", stats=payload, error_summary=str(exc))
                        repository.upsert_eis_cursor(
                            {
                                "region_code": normalized_region,
                                "subsystem_type": "PRIZ",
                                "document_type": document_type,
                                "last_requested_date": source_date,
                                "status": "failed",
                                "consecutive_failures": 1,
                                "next_retry_at": None,
                            }
                        )
                if effective_concurrency == 1:
                    time.sleep(0.2)
    return result


def _regions_for_mode(mode: SyncMode, regions: list[str] | None) -> list[str]:
    if regions:
        return regions
    if mode == "nationwide":
        return list(ALL_RUSSIAN_REGIONS)
    return list(DEFAULT_TARGET_REGIONS)
