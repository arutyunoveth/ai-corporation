from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from src.tender_research.config import TenderResearchConfig
from src.tender_research.eis_loader import EisTenderLoader
from src.tender_research.registry_discovery import (
    DiscoveredRegistryNumber,
    DiscoveryResult,
    RegistryNumberDiscovery,
    _parse_registry_numbers_from_html,
)


class TestParseRegistryNumbersFromHtml:
    def test_extracts_from_eis_url_pattern(self):
        html = '<a href="/epz/order/notice/ea44/view/common-info.html?regNumber=0373200008225000004">'
        assert _parse_registry_numbers_from_html(html) == ["0373200008225000004"]

    def test_extracts_multiple_numbers(self):
        html = """
        <a href="?regNumber=0373200008225000004">one</a>
        <a href="?regNumber=0373200008225000005">two</a>
        """
        assert _parse_registry_numbers_from_html(html) == [
            "0373200008225000004",
            "0373200008225000005",
        ]

    def test_deduplicates(self):
        html = """<a href="?regNumber=0373200008225000004">x</a>
                   <a href="?regNumber=0373200008225000004">y</a>"""
        assert _parse_registry_numbers_from_html(html) == ["0373200008225000004"]

    def test_fallback_to_plain_regex(self):
        html = "Some text 0373200008225000004 and more"
        assert _parse_registry_numbers_from_html(html) == ["0373200008225000004"]

    def test_ignores_short_numbers(self):
        html = "1234567890123456 and 0373200008225000004"
        assert _parse_registry_numbers_from_html(html) == ["0373200008225000004"]

    def test_returns_empty_for_no_match(self):
        assert _parse_registry_numbers_from_html("<html></html>") == []


class TestRegistryNumberDiscovery:
    def test_seed_file_returns_numbers(self):
        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("# comment\n0373200008225000004\n0373200008225000005\n")
            seed_path = f.name
        try:
            config = TenderResearchConfig(
                eis_mode="demo",
                eis_seed_file=seed_path,
            )
            discovery = RegistryNumberDiscovery(config=config)
            result = discovery._seed_file(limit=None)
            assert len(result.numbers) == 2
            assert result.numbers[0].registry_number == "0373200008225000004"
            assert result.numbers[0].source == "seed_file"
            assert result.numbers[1].registry_number == "0373200008225000005"
        finally:
            Path(seed_path).unlink(missing_ok=True)

    def test_seed_file_respects_limit(self):
        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("0373200008225000004\n0373200008225000005\n0373200008225000006\n")
            seed_path = f.name
        try:
            config = TenderResearchConfig(eis_seed_file=seed_path)
            discovery = RegistryNumberDiscovery(config=config)
            result = discovery._seed_file(limit=2)
            assert len(result.numbers) == 2
        finally:
            Path(seed_path).unlink(missing_ok=True)

    def test_seed_file_returns_empty_when_missing(self):
        config = TenderResearchConfig(eis_seed_file="/tmp/nonexistent_seed_test.txt")
        discovery = RegistryNumberDiscovery(config=config)
        result = discovery._seed_file()
        assert len(result.numbers) == 0

    def test_seed_file_skips_comments_and_blanks(self):
        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("\n\n# comment\n0373200008225000004\n\n# another\n")
            seed_path = f.name
        try:
            config = TenderResearchConfig(eis_seed_file=seed_path)
            discovery = RegistryNumberDiscovery(config=config)
            result = discovery._seed_file()
            assert len(result.numbers) == 1
            assert result.numbers[0].registry_number == "0373200008225000004"
        finally:
            Path(seed_path).unlink(missing_ok=True)

    def test_build_public_search_url(self):
        config = TenderResearchConfig()
        discovery = RegistryNumberDiscovery(config=config)
        url = discovery._build_public_search_url(days_back=3, page=1)
        assert "publishDateFrom=" in url
        assert "publishDateTo=" in url
        assert "pageNumber=1" in url
        assert "fz44=on" in url
        assert "fz223=on" in url

    def test_discover_with_invalid_source_raises(self):
        config = TenderResearchConfig()
        discovery = RegistryNumberDiscovery(config=config)
        with pytest.raises(Exception):
            discovery.discover(source="invalid_source")

    def test_discovered_registry_number_dataclass(self):
        d = DiscoveredRegistryNumber(
            registry_number="0373200008225000004",
            source="seed_file",
            tender_title="Test",
            external_id="123",
        )
        assert d.registry_number == "0373200008225000004"
        assert d.source == "seed_file"
        assert d.tender_title == "Test"
        assert d.external_id == "123"

    def test_discovery_result_dataclass(self):
        r = DiscoveryResult(
            numbers=[DiscoveredRegistryNumber("0373200008225000004", "seed_file")],
            selected_source="seed_file",
            is_demo=True,
            warnings=["test warning"],
        )
        assert len(r.numbers) == 1
        assert r.selected_source == "seed_file"
        assert r.is_demo is True
        assert r.warnings == ["test warning"]


class TestRealVsDemoDiscrimination:
    def test_backend_search_ignores_demo_in_real_mode(self):
        config = TenderResearchConfig(
            eis_mode="real",
            allow_demo_discovery=False,
        )
        discovery = RegistryNumberDiscovery(config=config)
        result = discovery.discover(source="backend_search", days_back=365, limit=10)
        assert len(result.numbers) == 0
        assert len(result.warnings) > 0
        assert "demo" in result.warnings[0].lower()

    def test_auto_can_use_demo_backend_search_in_demo_mode(self):
        config = TenderResearchConfig(
            eis_mode="demo",
            allow_demo_discovery=True,
        )
        discovery = RegistryNumberDiscovery(config=config)
        result = discovery.discover(source="auto", days_back=365, limit=10)
        assert result.selected_source == "backend_search"

    def test_backend_search_returns_is_demo_true(self):
        config = TenderResearchConfig(eis_mode="demo")
        discovery = RegistryNumberDiscovery(config=config)
        result = discovery.discover(source="backend_search", days_back=365, limit=10)
        assert len(result.numbers) > 0
        for rn in result.numbers:
            assert rn.is_demo is True
        assert result.is_demo is True

    def test_backend_search_real_mode_allows_demo_when_allowed(self):
        config = TenderResearchConfig(
            eis_mode="real",
            allow_demo_discovery=True,
        )
        discovery = RegistryNumberDiscovery(config=config)
        result = discovery.discover(source="backend_search", days_back=365, limit=10)
        assert len(result.numbers) > 0
        assert result.is_demo is True

    def test_seed_file_custom_path_via_parameter(self):
        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("0373200008225000004\n")
            seed_path = f.name
        try:
            config = TenderResearchConfig(eis_mode="demo")
            discovery = RegistryNumberDiscovery(config=config)
            result = discovery.discover(source="seed_file", seed_file=seed_path)
            assert len(result.numbers) == 1
            assert result.numbers[0].registry_number == "0373200008225000004"
        finally:
            Path(seed_path).unlink(missing_ok=True)

    def test_proxy_bypass_config(self):
        config = TenderResearchConfig(public_search_bypass_proxy=True)
        discovery = RegistryNumberDiscovery(config=config)
        url = discovery._build_public_search_url(days_back=3, page=1)
        assert url.startswith("https://zakupki.gov.ru")
        assert "pageNumber=1" in url
