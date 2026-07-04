from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.shared.db.base import Base
from src.tender_research.config import TenderResearchConfig
from src.tender_research.pipeline import TenderResearchPipeline
from src.tender_research.providers.public_44fz_search import PublicSearchStatus, PublicTenderDetail
from src.tender_research.registry_discovery import DiscoveredRegistryNumber, DiscoveryResult, SourceType
from src.tender_research.repository import TenderRepository


def _pipeline() -> TenderResearchPipeline:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    config = TenderResearchConfig(
        enabled=True,
        data_dir="/tmp/tender_research_limit_consistency",
        web_search_enabled=False,
        web_fetch_enabled=False,
    )
    pipeline = TenderResearchPipeline(session, config=config)
    pipeline.run_full = lambda tender_id: {"tender_id": tender_id, "documents_downloaded": 0, "documents_failed": 0}
    return pipeline


class FakePublicProvider:
    def fetch_detail(self, item_or_url=None, registry_number=None, card_url=None):
        return PublicTenderDetail(
            registry_number=registry_number,
            network_status=PublicSearchStatus.TIMEOUT,
            error_message="timed out",
            document_links=[],
        )


class FakeEisLoader:
    def fetch_by_registry_number(self, registry_number: str):
        return None

    def fetch_tender_documents(self, tender):
        return []


def test_run_discovered_batch_attempts_all_discovery_items_even_when_detail_fails():
    pipeline = _pipeline()
    pipeline._public_provider = FakePublicProvider()
    pipeline._eis = FakeEisLoader()

    discovered = [
        DiscoveredRegistryNumber(
            registry_number=f"0373200000000000{i:03d}",
            source="external_public_44fz",
            source_type=SourceType.EXTERNAL_PUBLIC_44FZ,
            tender_title=f"Title {i}",
            customer_name=f"Customer {i}",
            publication_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
            nmck_amount=float(i),
            source_url="https://zakupki.gov.ru/search",
            card_url=f"https://zakupki.gov.ru/card/{i}",
        )
        for i in range(30)
    ]
    pipeline.discover_registry_numbers = lambda **kwargs: DiscoveryResult(
        numbers=discovered,
        selected_source="external_public_44fz",
        selected_source_type=SourceType.EXTERNAL_PUBLIC_44FZ,
        requested_limit=30,
        effective_limit=30,
        requested_page_size=30,
        effective_page_size=30,
        pages_read=1,
        source_url="https://zakupki.gov.ru/epz/order/extendedsearch/results.html",
        discovered_count=30,
        items_raw_count=30,
        items_with_registry_number=30,
        skipped_without_registry_number=0,
        items_after_dedupe=30,
        items_after_demo_filter=30,
        network_status=PublicSearchStatus.SUCCESS,
    )

    results = pipeline.run_discovered_batch(source="external_public_44fz", limit=30, page_size=30)

    repo = TenderRepository(pipeline._session)
    assert len(results) == 30
    assert repo.count_tenders() == 30
    assert pipeline.last_discovered_batch_summary["discovered_count"] == 30
    assert pipeline.last_discovered_batch_summary["ingest_attempts"] == 30
    assert pipeline.last_discovered_batch_summary["detail_fetch_attempts"] == 30
    assert pipeline.last_discovered_batch_summary["detail_fetch_success"] == 0
    assert pipeline.last_discovered_batch_summary["items_after_dedupe"] == 30
