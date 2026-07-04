from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from src.tender_research.browser.fetcher import WebPageFetcher
from src.tender_research.browser.requests_fetcher import RequestsFetcher
from src.tender_research.config import TenderResearchConfig, load_config
from src.tender_research.dedupe import content_hash, normalize_url, url_hash
from src.tender_research.document_store import download_tender_documents
from src.tender_research.eis_loader import EisTenderLoader
from src.tender_research.errors import (
    EisConnectionResetError,
    EisMissingTokenError,
    EisNoDataError,
    classify_eis_error,
)
from src.tender_research.providers.duckduckgo_html import DuckDuckGoHtmlSearchProvider
from src.tender_research.providers.manual_urls import ManualUrlsSearchProvider
from src.tender_research.query_builder import build_search_queries
from src.tender_research.rate_limit import RateLimiter
from src.tender_research.repository import TenderRepository
from src.tender_research.search_provider import SearchProvider

logger = logging.getLogger(__name__)


class TenderResearchPipeline:
    def __init__(
        self,
        session: Session,
        config: TenderResearchConfig | None = None,
        eis_loader: EisTenderLoader | None = None,
        search_provider: SearchProvider | None = None,
        web_fetcher: WebPageFetcher | None = None,
    ):
        self._session = session
        self._config = config or load_config()
        self._repo = TenderRepository(session)
        self._eis = eis_loader or EisTenderLoader(mode=self._config.eis_mode, discovery_mode=self._config.eis_discovery_mode)
        self._search_provider = search_provider or DuckDuckGoHtmlSearchProvider(
            timeout=int(self._config.web_search_timeout_seconds),
        )
        self._web_fetcher = web_fetcher or RequestsFetcher()
        self._search_limiter = RateLimiter(delay_seconds=self._config.web_search_delay_seconds)
        self._fetch_limiter = RateLimiter(delay_seconds=self._config.web_fetch_delay_seconds)

    # ── Step 1: Ingest tenders from EIS ──

    def ingest_eis_tenders(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        law_type: str | None = None,
        query: str | None = None,
    ) -> int:
        batch_limit = limit or self._config.batch_limit
        raw_tenders = self._eis.fetch_tenders(
            date_from=date_from,
            date_to=date_to,
            limit=batch_limit,
            law_type=law_type,
            query=query,
        )
        saved = 0
        for raw in raw_tenders:
            try:
                saved += self._save_one_tender(raw)
            except Exception as e:
                logger.error("Failed to ingest tender %s: %s", raw.external_id, e)
        self._session.commit()
        return saved

    def ingest_eis_by_registry_numbers(
        self,
        registry_numbers: list[str],
        limit: int | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "total": len(registry_numbers),
            "saved": 0,
            "skipped": 0,
            "errors": [],
            "connection_resets": 0,
            "no_data": 0,
            "missing_token": False,
        }
        numbers = registry_numbers[:limit] if limit else registry_numbers
        for rn in numbers:
            try:
                raw = self._eis.fetch_by_registry_number(rn)
                if raw is None:
                    result["skipped"] += 1
                    continue
                self._save_one_tender(raw)
                result["saved"] += 1
            except EisMissingTokenError:
                result["missing_token"] = True
                result["errors"].append(f"{rn}: token missing")
                break
            except EisConnectionResetError:
                result["connection_resets"] += 1
                result["errors"].append(f"{rn}: connection reset")
            except EisNoDataError:
                result["no_data"] += 1
            except Exception as e:
                result["errors"].append(f"{rn}: {e}")
        self._session.commit()
        return result

    def _save_one_tender(self, raw: EisTenderRaw) -> int:
        upsert_data = self._normalize_tender(raw)
        tender = self._repo.upsert_tender(upsert_data.tender)
        if upsert_data.customer:
            self._repo.upsert_customer(upsert_data.customer)
        for doc_data in upsert_data.documents:
            doc_data["tender_id"] = tender.id
            self._repo.upsert_document(doc_data)
        self._save_raw_payload(tender, raw)
        return 1

    # ── Step 2: Download documents ──

    def download_documents(self, tender_id: str) -> dict[str, int]:
        tender = self._repo.get_tender_by_id(tender_id)
        if not tender:
            return {"downloaded": 0, "failed": 0, "error": "Tender not found"}
        self._session.refresh(tender)
        result = download_tender_documents(self._repo, tender, self._config)
        self._session.commit()
        return result

    # ── Step 3: Build search queries ──

    def build_search_queries(self, tender_id: str) -> int:
        tender = self._repo.get_tender_by_id(tender_id)
        if not tender:
            return 0
        queries = build_search_queries(
            tender_title=tender.title,
            customer_name=tender.customer_name,
            customer_inn=tender.customer_inn,
            registry_number=tender.registry_number,
            purchase_number=tender.purchase_number,
            max_queries=self._config.web_search_max_queries_per_tender,
        )
        count = 0
        for q in queries:
            q.provider = self._config.web_search_provider
            self._repo.upsert_search_query({
                "tender_id": tender.id,
                "query": q.query,
                "query_type": q.query_type,
                "provider": q.provider,
            })
            count += 1
        self._session.commit()
        return count

    # ── Step 4: Run web search ──

    def run_web_search(self, tender_id: str) -> int:
        tender = self._repo.get_tender_by_id(tender_id)
        if not tender or not self._config.web_search_enabled:
            return 0
        pending = self._repo.list_pending_search_queries(tender.id, self._config.web_search_provider)
        total = 0
        for sq in pending:
            self._search_limiter.wait()
            try:
                results = self._search_provider.search(
                    sq.query,
                    limit=self._config.web_search_max_results_per_query,
                )
                for r in results:
                    self._repo.upsert_search_result({
                        "tender_id": tender.id,
                        "query_id": sq.id,
                        "provider": sq.provider,
                        "rank": r.rank,
                        "title": r.title,
                        "url": r.url,
                        "normalized_url": r.normalized_url,
                        "snippet": r.snippet,
                        "display_url": r.display_url,
                        "raw_result": r.raw_result,
                        "url_hash": r.url_hash or url_hash(r.normalized_url),
                    })
                    total += 1
                sq.status = "done"
                sq.results_count = len(results)
                sq.executed_at = datetime.now(timezone.utc)
            except Exception as e:
                sq.status = "failed"
                sq.error_message = str(e)
            self._session.flush()
        self._session.commit()
        return total

    # ── Step 5: Fetch search result pages ──

    def fetch_search_results(self, tender_id: str, max_pages: int | None = None) -> dict[str, int]:
        tender = self._repo.get_tender_by_id(tender_id)
        if not tender or not self._config.web_fetch_enabled:
            return {"fetched": 0, "failed": 0}
        max_pages = max_pages or self._config.web_fetch_max_pages_per_tender
        results = self._repo.list_unfetched_results(tender.id, max_results=max_pages)
        fetched = 0
        failed = 0
        for sr in results:
            self._fetch_limiter.wait()
            fetch_result = self._web_fetcher.fetch(
                sr.url,
                timeout=self._config.web_fetch_timeout_seconds,
                max_size_mb=self._config.web_fetch_max_file_size_mb,
            )
            wp_path = self._save_web_page(tender, fetch_result)
            wp_path["search_result_id"] = sr.id
            self._repo.upsert_web_page(wp_path)
            if fetch_result.status == "fetched":
                fetched += 1
            else:
                failed += 1
            self._session.flush()
        self._session.commit()
        return {"fetched": fetched, "failed": failed}

    # ── Run full pipeline for one tender ──

    def run_full(self, tender_id: str) -> dict[str, int | str]:
        result: dict[str, int | str] = {"tender_id": tender_id}
        try:
            docs = self.download_documents(tender_id)
            result["documents_downloaded"] = docs.get("downloaded", 0)
            result["documents_failed"] = docs.get("failed", 0)
        except Exception as e:
            result["documents_error"] = str(e)

        try:
            queries_built = self.build_search_queries(tender_id)
            result["queries_built"] = queries_built
        except Exception as e:
            result["queries_error"] = str(e)

        try:
            search_results = self.run_web_search(tender_id)
            result["search_results_saved"] = search_results
        except Exception as e:
            result["search_error"] = str(e)

        try:
            pages = self.fetch_search_results(tender_id)
            result["pages_fetched"] = pages.get("fetched", 0)
            result["pages_failed"] = pages.get("failed", 0)
        except Exception as e:
            result["fetch_error"] = str(e)

        return result

    # ── Run batch ──

    def run_batch(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        law_type: str | None = None,
        query: str | None = None,
        web_search: bool = False,
    ) -> list[dict[str, int | str]]:
        batch_limit = limit or self._config.batch_limit
        raw_tenders = self._eis.fetch_tenders(
            date_from=date_from,
            date_to=date_to,
            limit=batch_limit,
            law_type=law_type,
            query=query,
        )
        results: list[dict[str, int | str]] = []
        for raw in raw_tenders:
            try:
                upsert_data = self._normalize_tender(raw)
                tender = self._repo.upsert_tender(upsert_data.tender)
                if upsert_data.customer:
                    self._repo.upsert_customer(upsert_data.customer)
                for doc_data in upsert_data.documents:
                    doc_data["tender_id"] = tender.id
                    self._repo.upsert_document(doc_data)
                self._save_raw_payload(tender, raw)
                self._session.commit()
            except Exception as e:
                logger.error("Failed to save tender %s: %s", raw.external_id, e)
                results.append({"tender_id": raw.external_id, "error": str(e)})
                continue

            r = self.run_full(tender.id)
            r["external_id"] = raw.external_id
            r["title"] = tender.title
            results.append(r)

        return results

    # ── Normalization ──

    def _normalize_tender(self, raw: EisTenderRaw) -> TenderUpsertData:
        from src.tender_research.schemas import TenderUpsertData  # noqa

        tender_data = {
            "source": "eis",
            "external_id": raw.external_id,
            "registry_number": raw.registry_number,
            "purchase_number": raw.purchase_number,
            "law_type": raw.law_type,
            "title": raw.title,
            "description": raw.description,
            "customer_name": raw.customer_name,
            "customer_inn": raw.customer_inn,
            "customer_kpp": raw.customer_kpp,
            "region": raw.region,
            "nmck_amount": raw.nmck_amount,
            "currency": raw.currency,
            "publication_date": raw.publication_date,
            "application_deadline": raw.application_deadline,
            "auction_date": raw.auction_date,
            "status": raw.status,
            "eis_url": raw.eis_url,
            "raw_payload": raw.raw_payload,
        }
        hash_input = raw.title + (raw.customer_name or "") + raw.external_id
        tender_data["content_hash"] = content_hash(hash_input)

        customer_data = None
        if raw.customer_name:
            customer_data = {
                "name": raw.customer_name,
                "inn": raw.customer_inn,
                "kpp": raw.customer_kpp,
                "region": raw.region,
                "raw_last_payload": raw.raw_payload,
            }

        documents = []
        for doc in raw.documents or self._eis.fetch_tender_documents(raw):
            documents.append({
                "source_document_id": doc.source_document_id,
                "file_name": doc.file_name,
                "file_url": doc.file_url,
                "content_type": doc.content_type,
                "size_bytes": doc.size_bytes,
                "raw_meta": doc.raw_meta,
            })

        return TenderUpsertData(
            tender=tender_data,
            customer=customer_data,
            documents=documents,
        )

    def _save_raw_payload(self, tender: ProcurementTender, raw: EisTenderRaw) -> None:
        tender_dir = (
            Path(self._config.data_dir)
            / "tenders"
            / "eis"
            / _safe_dirname(raw.external_id)
            / "raw"
        )
        tender_dir.mkdir(parents=True, exist_ok=True)
        payload_path = tender_dir / "eis_payload.json"
        if payload_path.exists():
            existing = json.loads(payload_path.read_text(encoding="utf-8"))
            existing["last_seen_at"] = datetime.now(timezone.utc).isoformat()
            payload_path.write_text(
                json.dumps(existing, ensure_ascii=False, default=str), encoding="utf-8"
            )
            return
        raw_dict = {
            "external_id": raw.external_id,
            "title": raw.title,
            "customer_name": raw.customer_name,
            "customer_inn": raw.customer_inn,
            "law_type": raw.law_type,
            "nmck_amount": raw.nmck_amount,
            "publication_date": str(raw.publication_date) if raw.publication_date else None,
            "application_deadline": str(raw.application_deadline) if raw.application_deadline else None,
            "raw_payload": raw.raw_payload,
            "first_seen_at": datetime.now(timezone.utc).isoformat(),
        }
        payload_path.write_text(
            json.dumps(raw_dict, ensure_ascii=False, default=str), encoding="utf-8"
        )
        self._repo.upsert_artifact({
            "tender_id": tender.id,
            "artifact_type": "eis_payload",
            "source": "eis",
            "local_path": str(payload_path),
            "sha256": hashlib.sha256(
                json.dumps(raw_dict, ensure_ascii=False, default=str).encode()
            ).hexdigest(),
            "size_bytes": payload_path.stat().st_size,
            "content_type": "application/json",
        })

    def _save_web_page(self, tender: ProcurementTender, fr: FetchResult) -> dict:
        tender_dir = (
            Path(self._config.data_dir)
            / "tenders"
            / "eis"
            / _safe_dirname(tender.external_id)
            / "web"
        )
        html_dir = tender_dir / "pages"
        text_dir = tender_dir / "extracted_text"
        html_dir.mkdir(parents=True, exist_ok=True)
        text_dir.mkdir(parents=True, exist_ok=True)

        html_path = None
        text_path = None
        if fr.html:
            html_path = html_dir / f"{fr.url_hash}.html"
            html_path.write_text(fr.html, encoding="utf-8")
        if fr.extracted_text:
            text_path = text_dir / f"{fr.url_hash}.txt"
            text_path.write_text(fr.extracted_text, encoding="utf-8")

        return {
            "tender_id": tender.id,
            "url": fr.url,
            "normalized_url": fr.normalized_url,
            "url_hash": fr.url_hash,
            "fetcher": fr.fetcher,
            "fetch_status": fr.status,
            "http_status": fr.http_status,
            "content_type": fr.content_type,
            "final_url": fr.final_url,
            "html_path": str(html_path) if html_path else None,
            "text_path": str(text_path) if text_path else None,
            "extracted_title": fr.extracted_title,
            "extracted_text_chars": len(fr.extracted_text) if fr.extracted_text else None,
            "raw_meta": {},
            "error_message": fr.error_message,
            "fetched_at": datetime.now(timezone.utc),
        }


def _safe_dirname(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in "_-")[:100] or "unknown"
