from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.tender_research.config import TenderResearchConfig
from src.tender_research.eis_loader import EisTenderLoader
from src.tender_research.errors import DiscoveryEmptyError, DiscoveryError
from src.tender_research.providers.public_44fz_search import (
    Public44FzSearchProvider,
    PublicSearchStatus,
    PublicTenderSearchPage,
)

logger = logging.getLogger(__name__)

_REGISTRY_NUMBER_RE = re.compile(r"\b(\d{19})\b")
_EIS_URL_RE = re.compile(r"regNumber=(\d{19})")


class SourceType:
    BACKEND_SEARCH_REAL = "backend_search_real"
    EXTERNAL_PUBLIC_44FZ = "external_public_44fz"
    LOCAL_DB = "local_db"
    SEED_FILE = "seed_file"
    DEMO = "demo"
    UNAVAILABLE = "unavailable"
    NONE = "none"


@dataclass
class DiscoveredRegistryNumber:
    registry_number: str
    source: str = ""
    source_type: str = SourceType.NONE
    tender_title: str | None = None
    external_id: str | None = None
    is_demo: bool = False


@dataclass
class DiscoveryResult:
    numbers: list[DiscoveredRegistryNumber]
    selected_source: str
    selected_source_type: str = SourceType.NONE
    is_demo: bool = False
    pages_read: int = 0
    page_size: int = 0
    discovered_count: int = 0
    skipped_without_registry_number: int = 0
    network_status: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _parse_registry_numbers_from_html(html: str) -> list[str]:
    seen: set[str] = set()
    numbers: list[str] = []
    for match in _EIS_URL_RE.finditer(html):
        rn = match.group(1)
        if rn not in seen:
            seen.add(rn)
            numbers.append(rn)
    if not numbers:
        for match in _REGISTRY_NUMBER_RE.finditer(html):
            rn = match.group(1)
            if rn not in seen:
                seen.add(rn)
                numbers.append(rn)
    return numbers


class RegistryNumberDiscovery:
    def __init__(
        self,
        config: TenderResearchConfig | None = None,
        eis_loader: EisTenderLoader | None = None,
    ):
        self._config = config or TenderResearchConfig()
        self._eis = eis_loader or EisTenderLoader(
            mode=self._config.eis_mode,
            discovery_mode=self._config.eis_discovery_mode,
        )
        self._public_provider = Public44FzSearchProvider(
            timeout_seconds=self._config.public_search_timeout_seconds,
            delay_seconds=self._config.public_search_delay_seconds,
            bypass_proxy=self._config.public_search_bypass_proxy,
            no_proxy_domains=self._config.public_search_no_proxy_domains,
        )

    def discover(
        self,
        source: str = "auto",
        days_back: int | None = None,
        limit: int | None = None,
        seed_file: str | None = None,
        page_size: int = 30,
    ) -> DiscoveryResult:
        source = source or self._config.registry_discovery_source
        days_back = days_back if days_back is not None else self._config.registry_discovery_days_back
        limit = limit if limit is not None else self._config.registry_discovery_limit

        if source in ("auto", "auto_discover"):
            return self._auto_discover(days_back=days_back, limit=limit, seed_file=seed_file, page_size=page_size)
        elif source == "external_public_44fz":
            return self._external_public_44fz(days_back=days_back, limit=limit, page_size=page_size)
        elif source == "seed_file":
            return self._seed_file(limit=limit, seed_file=seed_file)
        elif source == "local_db":
            return self._local_db(days_back=days_back, limit=limit)
        elif source == "demo":
            return self._demo_discover(days_back=days_back, limit=limit)
        elif source in ("backend_search", "backend_search_real"):
            return self._backend_search_real(days_back=days_back, limit=limit)
        else:
            msg = f"Unknown discovery source: {source}"
            raise DiscoveryError(msg)

    def _auto_discover(
        self,
        days_back: int,
        limit: int,
        seed_file: str | None,
        page_size: int,
    ) -> DiscoveryResult:
        warnings: list[str] = []

        result = self._external_public_44fz(days_back=days_back, limit=limit, page_size=page_size)
        if result.numbers and not result.is_demo:
            result.warnings = warnings
            return result
        if result.network_status in (PublicSearchStatus.BLOCKED, PublicSearchStatus.TIMEOUT, PublicSearchStatus.BAD_GATEWAY):
            warnings.append(f"external_public_44fz is blocked in current network: {result.network_status}")

        result = self._seed_file(limit=limit, seed_file=seed_file)
        if result.numbers:
            result.warnings = warnings
            return result

        if self._config.allow_demo_discovery:
            warnings.append("No real data found, using demo as fallback")
            result = self._demo_discover(days_back=days_back, limit=limit)
            result.warnings = warnings
            return result

        warnings.append("No real data found and allow_demo_discovery is false")
        return DiscoveryResult(
            numbers=[],
            selected_source="auto",
            selected_source_type=SourceType.NONE,
            warnings=warnings,
            network_status="no_source_available",
        )

    def _external_public_44fz(
        self,
        days_back: int,
        limit: int,
        page_size: int = 30,
    ) -> DiscoveryResult:
        date_from = datetime.now(timezone.utc).date() - timedelta(days=days_back)
        date_to = datetime.now(timezone.utc).date()
        max_pages = max(1, (limit + page_size - 1) // page_size)
        max_pages = min(max_pages, 10)

        pages = self._public_provider.search_pages(
            query=None,
            date_from=date_from,
            date_to=date_to,
            max_pages=max_pages,
            page_size=page_size,
        )

        first_status = pages[0].status if pages else PublicSearchStatus.EMPTY
        network_status = first_status
        if first_status not in (PublicSearchStatus.SUCCESS, PublicSearchStatus.EMPTY):
            return DiscoveryResult(
                numbers=[],
                selected_source="external_public_44fz",
                selected_source_type=SourceType.EXTERNAL_PUBLIC_44FZ,
                pages_read=0,
                page_size=page_size,
                network_status=first_status,
                errors=[pages[0].error or f"Network status: {first_status}"] if pages else [],
                warnings=[f"external_public_44fz is {first_status}: {pages[0].error}" if pages else f"external_public_44fz is {first_status}"],
            )

        numbers = self._public_provider.extract_registry_numbers(pages)
        discovered = [
            DiscoveredRegistryNumber(registry_number=rn, source="external_public_44fz", source_type=SourceType.EXTERNAL_PUBLIC_44FZ)
            for rn in numbers[:limit]
        ]

        successes = sum(1 for p in pages if p.status == PublicSearchStatus.SUCCESS)
        return DiscoveryResult(
            numbers=discovered,
            selected_source="external_public_44fz",
            selected_source_type=SourceType.EXTERNAL_PUBLIC_44FZ,
            pages_read=len(pages),
            page_size=page_size,
            discovered_count=len(discovered),
            network_status=network_status,
            errors=[],
            warnings=[f"external_public_44fz read {len(pages)} pages, found {len(numbers)} numbers, {len(pages) - successes} pages non-success"],
        )

    def _seed_file(
        self,
        limit: int | None = None,
        seed_file: str | None = None,
    ) -> DiscoveryResult:
        seed_path_str = seed_file or self._config.eis_seed_file
        seed_path = Path(seed_path_str)
        if not seed_path.exists():
            msg = f"Seed file not found: {seed_path}"
            logger.warning(msg)
            return DiscoveryResult(
                numbers=[],
                selected_source="seed_file",
                selected_source_type=SourceType.SEED_FILE,
                warnings=[msg],
            )

        if seed_path.suffix.lower() == ".json":
            return self._seed_from_json(seed_path, limit)

        lines = [
            line.strip() for line in seed_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not lines:
            return DiscoveryResult(
                numbers=[],
                selected_source="seed_file",
                selected_source_type=SourceType.SEED_FILE,
            )
        selected = lines[:limit] if limit else lines
        numbers = [
            DiscoveredRegistryNumber(registry_number=rn, source="seed_file", source_type=SourceType.SEED_FILE)
            for rn in selected
        ]
        return DiscoveryResult(
            numbers=numbers,
            selected_source="seed_file",
            selected_source_type=SourceType.SEED_FILE,
            discovered_count=len(numbers),
        )

    def _seed_from_json(self, seed_path: Path, limit: int | None = None) -> DiscoveryResult:
        try:
            raw = json.loads(seed_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            return DiscoveryResult(
                numbers=[],
                selected_source="seed_file",
                selected_source_type=SourceType.SEED_FILE,
                errors=[f"Failed to parse JSON seed: {exc}"],
            )
        if isinstance(raw, dict):
            items = raw.get("items", raw.get("numbers", []))
        elif isinstance(raw, list):
            items = raw
        else:
            return DiscoveryResult(
                numbers=[],
                selected_source="seed_file",
                selected_source_type=SourceType.SEED_FILE,
                errors=["Unexpected JSON seed format, expected list or dict with items/numbers"],
            )
        if limit:
            items = items[:limit]
        numbers: list[DiscoveredRegistryNumber] = []
        for item in items:
            if isinstance(item, str):
                numbers.append(DiscoveredRegistryNumber(registry_number=item, source="seed_file", source_type=SourceType.SEED_FILE))
            elif isinstance(item, dict):
                rn = item.get("registry_number", item.get("reestr_number", item.get("number", "")))
                if rn:
                    numbers.append(DiscoveredRegistryNumber(
                        registry_number=str(rn),
                        source="seed_file",
                        source_type=SourceType.SEED_FILE,
                        tender_title=item.get("title"),
                        external_id=item.get("purchase_number"),
                    ))
        return DiscoveryResult(
            numbers=numbers,
            selected_source="seed_file",
            selected_source_type=SourceType.SEED_FILE,
            discovered_count=len(numbers),
        )

    def _local_db(
        self,
        days_back: int,
        limit: int,
    ) -> DiscoveryResult:
        date_from = datetime.now(timezone.utc) - timedelta(days=days_back)
        try:
            from src.tender_research.pipeline_utils import get_tenders_from_repo
            tenders = get_tenders_from_repo(date_from=date_from, limit=limit)
        except Exception as exc:
            return DiscoveryResult(
                numbers=[],
                selected_source="local_db",
                selected_source_type=SourceType.LOCAL_DB,
                errors=[f"Failed to query local database: {exc}"],
            )
        numbers: list[DiscoveredRegistryNumber] = []
        for t in tenders:
            rn = getattr(t, "registry_number", None)
            if rn:
                numbers.append(DiscoveredRegistryNumber(
                    registry_number=rn,
                    source="local_db",
                    source_type=SourceType.LOCAL_DB,
                    tender_title=getattr(t, "title", None),
                    external_id=getattr(t, "external_id", None),
                ))
        return DiscoveryResult(
            numbers=numbers,
            selected_source="local_db",
            selected_source_type=SourceType.LOCAL_DB,
            discovered_count=len(numbers),
        )

    def _backend_search_real(self, days_back: int, limit: int) -> DiscoveryResult:
        return DiscoveryResult(
            numbers=[],
            selected_source="backend_search_real",
            selected_source_type=SourceType.UNAVAILABLE,
            warnings=["backend_search_real is not implemented yet (no working external backend search endpoint)"],
            network_status="not_available",
        )

    def _demo_discover(self, days_back: int, limit: int) -> DiscoveryResult:
        date_from = datetime.now(timezone.utc) - timedelta(days=days_back)
        raw_tenders = self._eis.fetch_tenders(
            date_from=date_from,
            limit=limit,
        )
        numbers: list[DiscoveredRegistryNumber] = []
        skipped = 0
        for raw in raw_tenders:
            if raw.registry_number:
                numbers.append(DiscoveredRegistryNumber(
                    registry_number=raw.registry_number,
                    source="demo",
                    source_type=SourceType.DEMO,
                    tender_title=raw.title,
                    external_id=raw.external_id,
                    is_demo=True,
                ))
            else:
                skipped += 1
        return DiscoveryResult(
            numbers=numbers,
            selected_source="demo",
            selected_source_type=SourceType.DEMO,
            is_demo=True,
            discovered_count=len(numbers),
            skipped_without_registry_number=skipped,
        )
