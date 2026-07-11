from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.tender_research.providers.public_44fz_search import (
    Public44FzSearchProvider,
    PublicSearchStatus,
    PublicTenderSearchItem,
    PublicTenderSearchPage,
)


class FakePublicProvider(Public44FzSearchProvider):
    def __init__(self, pages: list[PublicTenderSearchPage]):
        super().__init__(timeout_seconds=5, delay_seconds=0, bypass_proxy=True)
        self._fake_pages = pages

    def search_pages(
        self,
        query=None,
        date_from=None,
        date_to=None,
        max_pages=3,
        page_size=30,
        law_type="44fz",
    ):
        return self._fake_pages


def _make_test_page(items: list[dict], page: int = 1) -> PublicTenderSearchPage:
    return PublicTenderSearchPage(
        items=[
            PublicTenderSearchItem(
                registry_number=item["registry_number"],
                purchase_number=item.get("purchase_number"),
                title=item.get("title"),
                customer_name=item.get("customer_name"),
                publication_date=item.get("publication_date"),
                source_url=item.get("source_url"),
                raw=item,
            )
            for item in items
        ],
        page=page,
        page_size=30,
        has_next=len(items) >= 30,
        status=PublicSearchStatus.SUCCESS,
        source_url="https://zakupki.gov.ru/epz/order/extendedsearch/results.html",
    )


_TEST_CARDS = [
    {"registry_number": "0373200008225000001", "title": "Закупка 1", "customer_name": "ООО Ромашка"},
    {"registry_number": "0373200008225000002", "title": "Закупка 2", "customer_name": "ООО Лютик"},
    {"registry_number": "0373200008225000003", "title": "Закупка 3", "customer_name": "АО Тест"},
]


class TestCollectRegistryNumbersTxt:
    def test_writes_txt(self):
        provider = FakePublicProvider([_make_test_page(_TEST_CARDS)])
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            output_path = f.name

        try:
            pages = provider.search_pages(max_pages=1, page_size=30)
            numbers = provider.extract_registry_numbers(pages)
            items = []
            for page_obj in pages:
                for item in page_obj.items:
                    items.append(item.registry_number)

            Path(output_path).write_text("\n".join(items) + "\n", encoding="utf-8")
            content = Path(output_path).read_text(encoding="utf-8").strip().split("\n")
            assert len(content) == 3
            assert content[0] == "0373200008225000001"
            assert content[1] == "0373200008225000002"
            assert content[2] == "0373200008225000003"
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_writes_json(self):
        provider = FakePublicProvider([_make_test_page(_TEST_CARDS)])
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            output_path = f.name

        try:
            pages = provider.search_pages(max_pages=1, page_size=30)
            items = []
            for page_obj in pages:
                for item in page_obj.items:
                    items.append({
                        "registry_number": item.registry_number,
                        "title": item.title,
                        "customer_name": item.customer_name,
                    })

            payload = json.dumps({
                "source": "external_public_44fz",
                "items": items,
            }, ensure_ascii=False, indent=2)
            Path(output_path).write_text(payload, encoding="utf-8")

            parsed = json.loads(Path(output_path).read_text(encoding="utf-8"))
            assert parsed["source"] == "external_public_44fz"
            assert len(parsed["items"]) == 3
            assert parsed["items"][0]["registry_number"] == "0373200008225000001"
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_output_excludes_demo(self):
        provider = FakePublicProvider([_make_test_page(_TEST_CARDS)])
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            output_path = f.name

        try:
            pages = provider.search_pages(max_pages=1, page_size=30)
            items = []
            for page_obj in pages:
                for item in page_obj.items:
                    items.append({
                        "registry_number": item.registry_number,
                        "title": item.title,
                    })

            payload = json.dumps({
                "source": "external_public_44fz",
                "items": items,
            }, ensure_ascii=False, indent=2)
            Path(output_path).write_text(payload, encoding="utf-8")

            parsed = json.loads(Path(output_path).read_text(encoding="utf-8"))
            assert len(parsed["items"]) == 3
            assert all("is_demo" not in item for item in parsed["items"])
        finally:
            Path(output_path).unlink(missing_ok=True)


class TestCollectRegistryNumbersNetwork:
    def test_blocked_network_status(self):
        blocked_page = PublicTenderSearchPage(
            page=1,
            page_size=30,
            status=PublicSearchStatus.BLOCKED,
            error="Connection reset by peer",
        )
        provider = FakePublicProvider([blocked_page])
        pages = provider.search_pages(max_pages=1, page_size=30)
        assert len(pages) == 1
        assert pages[0].status == PublicSearchStatus.BLOCKED

    def test_timeout_network_status(self):
        timeout_page = PublicTenderSearchPage(
            page=1,
            page_size=30,
            status=PublicSearchStatus.TIMEOUT,
            error="timed out",
        )
        provider = FakePublicProvider([timeout_page])
        pages = provider.search_pages(max_pages=1, page_size=30)
        assert pages[0].status == PublicSearchStatus.TIMEOUT

    def test_bad_gateway_status(self):
        bad_gateway_page = PublicTenderSearchPage(
            page=1,
            page_size=30,
            status=PublicSearchStatus.BAD_GATEWAY,
            error="HTTP 502",
        )
        provider = FakePublicProvider([bad_gateway_page])
        pages = provider.search_pages(max_pages=1, page_size=30)
        assert pages[0].status == PublicSearchStatus.BAD_GATEWAY
