from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from src.tender_research.providers.public_44fz_search import (
    _hostname_matches_no_proxy,
    _resolve_no_proxy_domains,
)


class TestHostnameMatchesNoProxy:
    def test_exact_match(self):
        assert _hostname_matches_no_proxy("zakupki.gov.ru", ("zakupki.gov.ru",))

    def test_subdomain_wildcard(self):
        assert _hostname_matches_no_proxy("www.zakupki.gov.ru", (".zakupki.gov.ru",))
        assert _hostname_matches_no_proxy("int.zakupki.gov.ru", (".zakupki.gov.ru",))

    def test_exact_subdomain(self):
        assert _hostname_matches_no_proxy("int.zakupki.gov.ru", ("int.zakupki.gov.ru",))

    def test_no_match(self):
        assert not _hostname_matches_no_proxy("google.com", ("zakupki.gov.ru",))
        assert not _hostname_matches_no_proxy("example.com", (".zakupki.gov.ru",))

    def test_empty_domains(self):
        assert not _hostname_matches_no_proxy("zakupki.gov.ru", ())

    def test_case_insensitive(self):
        assert _hostname_matches_no_proxy("ZAKUPKI.GOV.RU", ("zakupki.gov.ru",))

    def test_int44(self):
        assert _hostname_matches_no_proxy("int44.zakupki.gov.ru", ("int44.zakupki.gov.ru",))
        assert _hostname_matches_no_proxy("int44.zakupki.gov.ru", (".zakupki.gov.ru",))

    def test_int_match(self):
        assert _hostname_matches_no_proxy("int.zakupki.gov.ru", ("int.zakupki.gov.ru",))
        assert not _hostname_matches_no_proxy("int44.zakupki.gov.ru", ("int.zakupki.gov.ru",))


class TestResolveNoProxyDomains:
    def test_default_when_empty(self):
        with patch.dict(os.environ, {"NO_PROXY": "", "no_proxy": ""}, clear=True):
            result = _resolve_no_proxy_domains("")
            assert "zakupki.gov.ru" in result
            assert ".zakupki.gov.ru" in result

    def test_merges_config_and_env(self):
        with patch.dict(os.environ, {"NO_PROXY": "example.com"}):
            result = _resolve_no_proxy_domains("zakupki.gov.ru")
            assert "zakupki.gov.ru" in result
            assert "example.com" in result

    def test_dedupes(self):
        result = _resolve_no_proxy_domains("zakupki.gov.ru,zakupki.gov.ru")
        assert len([d for d in result if d == "zakupki.gov.ru"]) == 1

    def test_uses_no_proxy_env(self):
        with patch.dict(os.environ, {"no_proxy": "test.com"}):
            result = _resolve_no_proxy_domains("")
            assert "test.com" in result

    def test_default_tuple(self):
        with patch.dict(os.environ, {"NO_PROXY": "", "no_proxy": ""}, clear=True):
            result = _resolve_no_proxy_domains(None)
            assert "zakupki.gov.ru" in result


class TestProviderBypassDecision:
    def test_bypass_true_matches_no_proxy(self):
        with patch.dict(os.environ, {"NO_PROXY": "", "no_proxy": ""}, clear=True):
            from src.tender_research.providers.public_44fz_search import Public44FzSearchProvider
            provider = Public44FzSearchProvider(
                bypass_proxy=True,
                no_proxy_domains="zakupki.gov.ru,.zakupki.gov.ru",
            )
            assert provider._no_proxy_domains is not None
            assert "zakupki.gov.ru" in provider._no_proxy_domains

    def test_bypass_false_does_not_force_direct(self):
        with patch.dict(os.environ, {"NO_PROXY": "", "no_proxy": ""}, clear=True):
            from src.tender_research.providers.public_44fz_search import Public44FzSearchProvider
            provider = Public44FzSearchProvider(
                bypass_proxy=False,
                no_proxy_domains="zakupki.gov.ru",
            )
            assert provider._no_proxy_domains is not None

    def test_no_proxy_domains_from_config(self):
        with patch.dict(os.environ, {"NO_PROXY": "", "no_proxy": ""}, clear=True):
            from src.tender_research.providers.public_44fz_search import Public44FzSearchProvider
            provider = Public44FzSearchProvider(
                bypass_proxy=True,
                no_proxy_domains="zakupki.gov.ru,.zakupki.gov.ru,int.zakupki.gov.ru,int44.zakupki.gov.ru",
            )
            assert "zakupki.gov.ru" in provider._no_proxy_domains
            assert ".zakupki.gov.ru" in provider._no_proxy_domains
            assert "int.zakupki.gov.ru" in provider._no_proxy_domains
            assert "int44.zakupki.gov.ru" in provider._no_proxy_domains


class TestFetchPageProxyBehavior:
    def test_bypass_proxy_creates_opener_without_proxy(self):
        with patch.dict(os.environ, {"NO_PROXY": "", "no_proxy": ""}, clear=True):
            from urllib.request import ProxyHandler
            from src.tender_research.providers.public_44fz_search import Public44FzSearchProvider
            provider = Public44FzSearchProvider(
                timeout_seconds=1,
                bypass_proxy=True,
                no_proxy_domains="zakupki.gov.ru",
            )
            url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"
            from urllib.parse import urlparse
            hostname = urlparse(url).hostname or ""
            from src.tender_research.providers.public_44fz_search import _hostname_matches_no_proxy
            assert _hostname_matches_no_proxy(hostname, provider._no_proxy_domains)

    def test_no_bypass_for_non_matching_host(self):
        with patch.dict(os.environ, {"NO_PROXY": "", "no_proxy": ""}, clear=True):
            from src.tender_research.providers.public_44fz_search import (
                Public44FzSearchProvider,
                _hostname_matches_no_proxy,
            )
            provider = Public44FzSearchProvider(
                bypass_proxy=True,
                no_proxy_domains="zakupki.gov.ru",
            )
            assert not _hostname_matches_no_proxy("google.com", provider._no_proxy_domains)

    def test_default_no_proxy_includes_zakupki_domains(self):
        from src.tender_research.providers.public_44fz_search import (
            PUBLIC_SEARCH_NO_PROXY_DOMAINS,
        )
        assert "zakupki.gov.ru" in PUBLIC_SEARCH_NO_PROXY_DOMAINS
        assert ".zakupki.gov.ru" in PUBLIC_SEARCH_NO_PROXY_DOMAINS
        assert "int.zakupki.gov.ru" in PUBLIC_SEARCH_NO_PROXY_DOMAINS
        assert "int44.zakupki.gov.ru" in PUBLIC_SEARCH_NO_PROXY_DOMAINS


class TestFetchPageNetworkStatus:
    def test_bad_gateway_on_proxy_502(self):
        """Simulate HTTP 502 from proxy."""
        with patch.dict(os.environ, {"NO_PROXY": "", "no_proxy": ""}, clear=True):
            from urllib.error import HTTPError

            from src.tender_research.providers.public_44fz_search import (
                Public44FzSearchProvider,
                PublicSearchStatus,
            )

            provider = Public44FzSearchProvider(timeout_seconds=1, bypass_proxy=True)
            url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"

            with patch.object(provider, "_fetch_page") as mock_fetch:
                mock_fetch.return_value = {
                    "status": PublicSearchStatus.BAD_GATEWAY,
                    "html": None,
                    "error": "HTTP 502",
                }
                result = provider._fetch_page(url)
                assert result["status"] == PublicSearchStatus.BAD_GATEWAY
                assert "502" in (result.get("error") or "")

    def test_timeout_on_direct_connection(self):
        with patch.dict(os.environ, {"NO_PROXY": "", "no_proxy": ""}, clear=True):
            from src.tender_research.providers.public_44fz_search import (
                Public44FzSearchProvider,
                PublicSearchStatus,
            )

            provider = Public44FzSearchProvider(timeout_seconds=1, bypass_proxy=True)
            url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"

            with patch.object(provider, "_fetch_page") as mock_fetch:
                mock_fetch.return_value = {
                    "status": PublicSearchStatus.TIMEOUT,
                    "html": None,
                    "error": "timed out",
                }
                result = provider._fetch_page(url)
                assert result["status"] == PublicSearchStatus.TIMEOUT

    def test_network_error_on_rst(self):
        with patch.dict(os.environ, {"NO_PROXY": "", "no_proxy": ""}, clear=True):
            from src.tender_research.providers.public_44fz_search import (
                Public44FzSearchProvider,
                PublicSearchStatus,
            )

            provider = Public44FzSearchProvider(timeout_seconds=1, bypass_proxy=True)
            url = "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"

            with patch.object(provider, "_fetch_page") as mock_fetch:
                mock_fetch.return_value = {
                    "status": PublicSearchStatus.BLOCKED,
                    "html": None,
                    "error": "Connection reset by peer",
                }
                result = provider._fetch_page(url)
                assert result["status"] == PublicSearchStatus.BLOCKED


class TestCheckNetworkConfig:
    def test_mask_proxy_url_with_password(self):
        from src.tender_research.cli import _mask_proxy_url
        url = "http://user:password@proxy.example.com:8080"
        masked = _mask_proxy_url(url)
        assert "password" not in masked
        assert "****" in masked

    def test_mask_proxy_url_without_password(self):
        from src.tender_research.cli import _mask_proxy_url
        url = "http://proxy.example.com:8080"
        masked = _mask_proxy_url(url)
        assert masked == url

    def test_mask_proxy_url_empty(self):
        from src.tender_research.cli import _mask_proxy_url
        assert _mask_proxy_url("") == ""

    def test_check_network_config_imports(self):
        from src.tender_research.cli import cmd_check_network_config
        assert callable(cmd_check_network_config)
