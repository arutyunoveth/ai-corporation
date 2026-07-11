from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.shared.db.base import Base
from src.tender_research.config import TenderResearchConfig
from src.tender_research.pipeline import TenderResearchPipeline
from src.tender_research.providers.public_44fz_search import (
    PublicDocumentLink,
    PublicSearchStatus,
    PublicTenderDetail,
)
from src.tender_research.registry_discovery import DiscoveredRegistryNumber, SourceType
from src.tender_research.repository import TenderRepository


def _pipeline(tmp_dir: str) -> TenderResearchPipeline:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    config = TenderResearchConfig(
        enabled=True,
        data_dir=tmp_dir,
        web_search_enabled=False,
        web_fetch_enabled=False,
    )
    return TenderResearchPipeline(session, config=config)


class FakeProvider:
    def __init__(self, detail: PublicTenderDetail):
        self._detail = detail

    def fetch_detail(self, item_or_url=None, registry_number=None, card_url=None):
        return self._detail


def test_placeholder_tender_backfilled_with_real_metadata_and_documents(tmp_path):
    pipeline = _pipeline(str(tmp_path))
    repo = TenderRepository(pipeline._session)
    tender = repo.upsert_tender({
        "source": "eis",
        "external_id": "0373200000000000001",
        "registry_number": "0373200000000000001",
        "title": "Закупка 0373200000000000001",
    })
    pipeline._lookup_public_discovered_item = lambda registry_number, existing_tender=None: DiscoveredRegistryNumber(
        registry_number=registry_number,
        source="external_public_44fz",
        source_type=SourceType.EXTERNAL_PUBLIC_44FZ,
        tender_title="Реальный title",
        customer_name="Поиск заказчик",
    )
    pipeline._public_provider = FakeProvider(
        PublicTenderDetail(
            registry_number="0373200000000000001",
            title="Реальный title",
            customer_name="ГБУ Заказчик",
            publication_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
            nmck_amount=123.45,
            network_status=PublicSearchStatus.SUCCESS,
            document_links=[
                PublicDocumentLink(
                    title="Документ",
                    file_name="spec.pdf",
                    url="https://zakupki.gov.ru/spec.pdf?utm_source=x&doc=1",
                    content_type="application/pdf",
                    raw={"uid": "DOC-1"},
                )
            ],
        )
    )
    pipeline.download_documents = lambda tender_id: {"downloaded": 0, "failed": 0}

    summary = pipeline.backfill_public_metadata(limit=10, only_placeholders=True, with_documents=True)

    updated = repo.get_tender_by_external("eis", tender.external_id)
    assert updated.title == "Реальный title"
    assert updated.customer_name == "ГБУ Заказчик"
    assert updated.publication_date.date().isoformat() == "2026-07-01"
    assert updated.nmck_amount == 123.45
    assert repo.count_customers() == 1
    assert repo.count_documents() == 1
    assert summary["enriched_title_count"] == 1
    assert summary["documents_created"] == 1


def test_repeated_backfill_is_idempotent(tmp_path):
    pipeline = _pipeline(str(tmp_path))
    repo = TenderRepository(pipeline._session)
    repo.upsert_tender({
        "source": "eis",
        "external_id": "0373200000000000002",
        "registry_number": "0373200000000000002",
        "title": "Закупка 0373200000000000002",
    })
    pipeline._lookup_public_discovered_item = lambda registry_number, existing_tender=None: DiscoveredRegistryNumber(
        registry_number=registry_number,
        source="external_public_44fz",
        source_type=SourceType.EXTERNAL_PUBLIC_44FZ,
        tender_title="Реальный title 2",
    )
    pipeline._public_provider = FakeProvider(
        PublicTenderDetail(
            registry_number="0373200000000000002",
            title="Реальный title 2",
            network_status=PublicSearchStatus.SUCCESS,
            document_links=[
                PublicDocumentLink(
                    title="Документ",
                    file_name="spec.pdf",
                    url="https://zakupki.gov.ru/spec.pdf?utm_source=one&doc=2",
                    content_type="application/pdf",
                    raw={"uid": "DOC-2"},
                )
            ],
        )
    )
    pipeline.download_documents = lambda tender_id: {"downloaded": 0, "failed": 0}

    pipeline.backfill_public_metadata(limit=10, only_placeholders=True, with_documents=True)
    pipeline.backfill_public_metadata(limit=10, only_placeholders=True, with_documents=True)

    assert repo.count_documents() == 1


def test_dry_run_does_not_mutate_db(tmp_path):
    pipeline = _pipeline(str(tmp_path))
    repo = TenderRepository(pipeline._session)
    repo.upsert_tender({
        "source": "eis",
        "external_id": "0373200000000000003",
        "registry_number": "0373200000000000003",
        "title": "Закупка 0373200000000000003",
    })
    pipeline._session.commit()
    pipeline._lookup_public_discovered_item = lambda registry_number, existing_tender=None: DiscoveredRegistryNumber(
        registry_number=registry_number,
        source="external_public_44fz",
        source_type=SourceType.EXTERNAL_PUBLIC_44FZ,
        tender_title="Dry run title",
    )
    pipeline._public_provider = FakeProvider(
        PublicTenderDetail(
            registry_number="0373200000000000003",
            title="Dry run title",
            network_status=PublicSearchStatus.SUCCESS,
        )
    )

    pipeline.backfill_public_metadata(limit=10, only_placeholders=True, dry_run=True)

    unchanged = repo.get_tender_by_external("eis", "0373200000000000003")
    assert unchanged.title == "Закупка 0373200000000000003"


def test_non_placeholder_skipped_when_only_placeholders(tmp_path):
    pipeline = _pipeline(str(tmp_path))
    repo = TenderRepository(pipeline._session)
    repo.upsert_tender({
        "source": "eis",
        "external_id": "0373200000000000004",
        "registry_number": "0373200000000000004",
        "title": "Уже нормальный title",
    })
    pipeline._lookup_public_discovered_item = lambda registry_number, existing_tender=None: DiscoveredRegistryNumber(
        registry_number=registry_number,
        source="external_public_44fz",
        source_type=SourceType.EXTERNAL_PUBLIC_44FZ,
        tender_title="Новый title",
    )
    pipeline._public_provider = FakeProvider(
        PublicTenderDetail(
            registry_number="0373200000000000004",
            title="Новый title",
            network_status=PublicSearchStatus.SUCCESS,
        )
    )

    summary = pipeline.backfill_public_metadata(limit=10, only_placeholders=True)

    assert summary["placeholders_found"] == 0
