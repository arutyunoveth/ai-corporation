from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.tender_research.config import TenderResearchConfig
from src.tender_research.eis_loader import EisTenderLoader
from src.tender_research.errors import DiscoveryEmptyError, DiscoveryError

logger = logging.getLogger(__name__)

_REGISTRY_NUMBER_RE = re.compile(r"\b(\d{19})\b")
_EIS_URL_RE = re.compile(r"regNumber=(\d{19})")

PUBLIC_SEARCH_URL = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"


@dataclass
class DiscoveredRegistryNumber:
    registry_number: str
    source: str  # backend_search | eis_public_html | seed_file
    tender_title: str | None = None
    external_id: str | None = None
    is_demo: bool = False


@dataclass
class DiscoveryResult:
    numbers: list[DiscoveredRegistryNumber]
    selected_source: str
    is_demo: bool = False
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
        self._session = self._build_requests_session()

    def _build_requests_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(total=2, backoff_factor=1, status_forcelist=[502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        })
        return session

    def discover(
        self,
        source: str = "auto",
        days_back: int | None = None,
        limit: int | None = None,
        seed_file: str | None = None,
    ) -> DiscoveryResult:
        source = source or self._config.registry_discovery_source
        days_back = days_back if days_back is not None else self._config.registry_discovery_days_back
        limit = limit if limit is not None else self._config.registry_discovery_limit

        if source == "backend_search":
            return self._backend_search(days_back=days_back, limit=limit)
        elif source == "eis_public_html":
            return self._eis_public_html(days_back=days_back, limit=limit)
        elif source == "seed_file":
            return self._seed_file(limit=limit, seed_file=seed_file)
        elif source == "auto":
            return self._auto_discover(days_back=days_back, limit=limit, seed_file=seed_file)
        else:
            msg = f"Unknown discovery source: {source}"
            raise DiscoveryError(msg)

    def _auto_discover(
        self,
        days_back: int,
        limit: int,
        seed_file: str | None,
    ) -> DiscoveryResult:
        warnings: list[str] = []

        result = self._backend_search(days_back=days_back, limit=limit)
        if result.numbers and not result.is_demo:
            result.warnings = warnings
            return result
        if result.numbers and result.is_demo:
            if self._config.eis_mode == "real" and not self._config.allow_demo_discovery:
                warnings.append(
                    "backend_search returned demo data and was ignored in real mode "
                    "(set AI_CORP_TENDER_RESEARCH_ALLOW_DEMO_DISCOVERY=true to allow)"
                )
            else:
                result.warnings = warnings
                return result

        logger.info("backend_search returned no real results, falling back to eis_public_html")
        result = self._eis_public_html(days_back=days_back, limit=limit)
        if result.numbers:
            result.warnings = warnings
            return result

        logger.info("eis_public_html returned no results, falling back to seed_file")
        warnings.append("No results from backend_search or eis_public_html, using seed_file as fallback")
        result = self._seed_file(limit=limit, seed_file=seed_file)
        result.warnings = warnings
        return result

    def _backend_search(
        self,
        days_back: int,
        limit: int,
    ) -> DiscoveryResult:
        date_from = datetime.now(timezone.utc) - timedelta(days=days_back)
        raw_tenders = self._eis.fetch_tenders(
            date_from=date_from,
            limit=limit,
        )
        numbers: list[DiscoveredRegistryNumber] = []
        all_demo = True
        for raw in raw_tenders:
            if raw.registry_number:
                numbers.append(DiscoveredRegistryNumber(
                    registry_number=raw.registry_number,
                    source="backend_search",
                    tender_title=raw.title,
                    external_id=raw.external_id,
                    is_demo=raw.is_demo,
                ))
                if not raw.is_demo:
                    all_demo = False

        is_demo = all_demo and bool(numbers)

        if self._config.eis_mode == "real" and not self._config.allow_demo_discovery and is_demo:
            return DiscoveryResult(
                numbers=[],
                selected_source="backend_search",
                is_demo=True,
                warnings=[
                    "backend_search returned demo data and was ignored in real mode "
                    "(set AI_CORP_TENDER_RESEARCH_ALLOW_DEMO_DISCOVERY=true to allow)"
                ],
            )

        return DiscoveryResult(
            numbers=numbers,
            selected_source="backend_search",
            is_demo=is_demo,
        )

    def _eis_public_html(
        self,
        days_back: int,
        limit: int,
    ) -> DiscoveryResult:
        url = self._build_public_search_url(days_back)
        logger.info("Fetching EIS public search: %s", url)

        kwargs: dict = {
            "url": url,
            "timeout": self._config.public_search_timeout_seconds,
        }
        if self._config.public_search_bypass_proxy:
            kwargs["proxies"] = {"http": None, "https": None}
            logger.info("Bypassing proxy for EIS public search")

        try:
            resp = self._session.get(**kwargs)
            resp.raise_for_status()
        except requests.RequestException as e:
            msg = f"EIS public search request failed: {e}"
            logger.warning(msg)
            return DiscoveryResult(
                numbers=[],
                selected_source="eis_public_html",
                warnings=[msg],
            )

        html = resp.text
        numbers = _parse_registry_numbers_from_html(html)
        logger.info("Extracted %d registry numbers from public search", len(numbers))

        if self._config.public_search_delay_seconds > 0:
            time.sleep(self._config.public_search_delay_seconds)

        page = 2
        while len(numbers) < limit:
            paginated_url = self._build_public_search_url(days_back, page=page)
            try:
                pag_kwargs: dict = {
                    "url": paginated_url,
                    "timeout": self._config.public_search_timeout_seconds,
                }
                if self._config.public_search_bypass_proxy:
                    pag_kwargs["proxies"] = {"http": None, "https": None}
                resp = self._session.get(**pag_kwargs)
                resp.raise_for_status()
            except requests.RequestException:
                break
            more = _parse_registry_numbers_from_html(resp.text)
            before = len(numbers)
            for rn in more:
                if rn not in numbers:
                    numbers.append(rn)
            logger.info("Page %d: extracted %d new numbers (total %d)", page, len(numbers) - before, len(numbers))
            if not more:
                break
            if self._config.public_search_delay_seconds > 0:
                time.sleep(self._config.public_search_delay_seconds)
            page += 1

        discovered = [
            DiscoveredRegistryNumber(registry_number=rn, source="eis_public_html")
            for rn in numbers[:limit]
        ]
        return DiscoveryResult(
            numbers=discovered,
            selected_source="eis_public_html",
        )

    def _build_public_search_url(self, days_back: int, page: int = 1) -> str:
        date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%d.%m.%Y")
        date_to = datetime.now(timezone.utc).strftime("%d.%m.%Y")
        params = (
            f"searchString=&morf=1&fz44=on&fz223=on&currencyId=-1"
            f"&publishDateFrom={date_from}&publishDateTo={date_to}"
            f"&pageNumber={page}"
        )
        return f"{PUBLIC_SEARCH_URL}?{params}"

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
            return DiscoveryResult(numbers=[], selected_source="seed_file", warnings=[msg])
        lines = [
            line.strip() for line in seed_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not lines:
            return DiscoveryResult(numbers=[], selected_source="seed_file")
        selected = lines[:limit] if limit else lines
        numbers = [
            DiscoveredRegistryNumber(registry_number=rn, source="seed_file")
            for rn in selected
        ]
        return DiscoveryResult(numbers=numbers, selected_source="seed_file")
