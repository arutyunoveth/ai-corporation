from __future__ import annotations

import os
from unittest.mock import patch

from src.modules.tender_operator_agent_demo.eis_soap_transport import (
    SoapCapability,
    TransportStatus,
    post_soap,
    transport_status,
)
from src.modules.tender_operator_agent_demo.settings import (
    EisSoapGatewaySettings,
    _ENV_FILES_SEEDED,
    clear_zakupki_soap_settings_cache,
    get_zakupki_soap_settings,
)


def _make_gw(overrides: dict[str, str]) -> EisSoapGatewaySettings:
    env = {
        "EIS_SOAP_ENABLED": "1",
        "EIS_DOCS_SOAP_ENDPOINT": "https://int.zakupki.gov.ru/eis-integration/services/getDocsIP",
        "EIS_SEARCH_SOAP_ENDPOINT": "https://int44.zakupki.gov.ru/eis-integration/services-vbs",
        "EIS_DOCS_SOAP_TRANSPORT": "direct",
        "EIS_SEARCH_SOAP_TRANSPORT": "disabled",
        "ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN": "ind-token-123",
        "ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN": "",
        **overrides,
    }
    for k, v in env.items():
        os.environ[k] = v
    return EisSoapGatewaySettings.from_env()


def test_docs_default_enabled_search_default_disabled():
    gw = _make_gw({})
    assert gw.docs_available is True
    assert gw.search_available is False
    assert gw.docs_transport == "direct"
    assert gw.search_transport == "disabled"


def test_getdocsip_not_switched_to_servicesvbs_when_individual():
    gw = _make_gw({"ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN": "leg-token-456"})
    assert gw.docs_available is True
    assert gw.docs_transport == "direct"
    assert gw.search_available is False
    assert gw.search_transport == "disabled"


def test_legal_entity_token_does_not_break_docs_flow():
    gw = _make_gw({
        "ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN": "019f4785-0b55-7188-81ec-6c187bd9104e",
        "EIS_SEARCH_SOAP_TRANSPORT": "disabled",
    })
    assert gw.docs_available is True
    assert gw.individual_token_configured is True
    assert gw.legal_entity_token_configured is True


def test_search_direct_disabled_by_default():
    gw = _make_gw({})
    assert gw.search_transport == "disabled"
    assert gw.search_available is False
    status = transport_status(gw, SoapCapability.SEARCH)
    assert status == TransportStatus.DISABLED


def test_gateway_url_used_when_transport_gateway():
    gw = _make_gw({
        "EIS_SEARCH_SOAP_TRANSPORT": "gateway",
        "EIS_SOAP_GATEWAY_BASE_URL": "http://localhost:8099/gost",
        "ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN": "019f4785-0b55-7188-81ec-6c187bd9104e",
    })
    assert gw.search_available is True
    assert gw.search_transport == "gateway"
    assert "localhost:8099/gost/eis/search" in gw.search_url()
    assert gw.docs_url().startswith("https://int.zakupki.gov.ru")


def test_gateway_docs_url():
    gw = _make_gw({
        "EIS_DOCS_SOAP_TRANSPORT": "gateway",
        "EIS_SOAP_GATEWAY_BASE_URL": "http://gateway:8080",
    })
    assert "gateway:8080/eis/docs" in gw.docs_url()


def test_search_direct_returns_tls_incompatible():
    gw = _make_gw({
        "EIS_SEARCH_SOAP_TRANSPORT": "direct",
        "ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN": "019f4785-0b55-7188-81ec-6c187bd9104e",
    })
    status = transport_status(gw, SoapCapability.SEARCH)
    assert status == TransportStatus.TLS_INCOMPATIBLE


def test_post_soap_search_disabled_returns_controlled_status():
    gw = _make_gw({"EIS_SEARCH_SOAP_TRANSPORT": "disabled"})
    result = post_soap(gw, "<xml/>", capability=SoapCapability.SEARCH)
    assert result.status == TransportStatus.DISABLED
    assert result.xml is None


def test_post_soap_docs_disabled():
    gw = _make_gw({"EIS_DOCS_SOAP_TRANSPORT": "disabled"})
    result = post_soap(gw, "<xml/>", capability=SoapCapability.DOCS)
    assert result.status == TransportStatus.DISABLED
    assert result.xml is None


def test_post_soap_docs_direct_with_envelope():
    gw = _make_gw({
        "EIS_DOCS_SOAP_TRANSPORT": "direct",
        "ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN": "4a32757d-e951-4088-95fe-9c8ae7300e07",
    })
    result = post_soap(gw, "<xml/>", capability=SoapCapability.DOCS, soap_action="http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip")
    assert result.status in (TransportStatus.AVAILABLE, TransportStatus.GATEWAY_ONLY)
    if result.status == TransportStatus.AVAILABLE:
        assert result.http_status is not None


def test_fallback_old_env_var():
    old_indiv = os.environ.pop("ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN", None)
    old_token = os.environ.get("ZAKUPKI_GOV_RU_SOAP_TOKEN", "")
    # сбрасываем seed чтобы он перечитал env
    import src.modules.tender_operator_agent_demo.settings as s
    s._ENV_FILES_SEEDED = False
    env = {
        "EIS_SOAP_ENABLED": "1",
        "ZAKUPKI_GOV_RU_SOAP_TOKEN": "legacy-token-from-old-env",
        "EIS_DOCS_SOAP_TRANSPORT": "direct",
        "EIS_SEARCH_SOAP_TRANSPORT": "disabled",
    }
    for k, v in env.items():
        os.environ[k] = v
    gw = EisSoapGatewaySettings.from_env()
    assert gw.individual_token_configured is True
    assert gw.individual_token == "legacy-token-from-old-env"
    # restore
    if old_indiv:
        os.environ["ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN"] = old_indiv
    s._ENV_FILES_SEEDED = False


def test_zakupki_settings_compat_docs_endpoint():
    clear_zakupki_soap_settings_cache()
    env = {
        "EIS_SOAP_ENABLED": "1",
        "EIS_DOCS_SOAP_TRANSPORT": "direct",
        "EIS_SEARCH_SOAP_TRANSPORT": "disabled",
        "ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN": "ind-token-123",
        "ZAKUPKI_GOV_RU_SOAP_ENABLED": "1",
        "ZAKUPKI_GOV_RU_SOAP_TOKEN": "ind-token-123",
        "ZAKUPKI_GOV_RU_SOAP_TOKEN_OWNER": "individual",
    }
    for k, v in env.items():
        os.environ[k] = v
    s = get_zakupki_soap_settings()
    assert s.individual_mode is True
    assert s.configured is True
    assert "getDocsIP" in s.active_docs_endpoint


def test_search_transport_gateway_returns_available():
    gw = _make_gw({
        "EIS_SEARCH_SOAP_TRANSPORT": "gateway",
        "EIS_SOAP_GATEWAY_BASE_URL": "http://gw:8080",
        "ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN": "leg-token",
    })
    assert gw.search_available is True
    status = transport_status(gw, SoapCapability.SEARCH)
    assert status == TransportStatus.AVAILABLE


def test_search_transport_gateway_without_base_url():
    gw = _make_gw({
        "EIS_SEARCH_SOAP_TRANSPORT": "gateway",
        "EIS_SOAP_GATEWAY_BASE_URL": "",
        "ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN": "leg-token",
    })
    assert gw.search_available is False
    status = transport_status(gw, SoapCapability.SEARCH)
    assert status == TransportStatus.GATEWAY_ONLY


def test_docs_transport_gateway_without_base_url():
    gw = _make_gw({
        "EIS_DOCS_SOAP_TRANSPORT": "gateway",
        "EIS_SOAP_GATEWAY_BASE_URL": "",
    })
    assert gw.docs_available is False
    status = transport_status(gw, SoapCapability.DOCS)
    assert status == TransportStatus.GATEWAY_ONLY


def test_post_soap_search_gateway():
    gw = _make_gw({
        "EIS_SEARCH_SOAP_TRANSPORT": "gateway",
        "EIS_SOAP_GATEWAY_BASE_URL": "http://gw:8080",
        "ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN": "leg-token",
    })
    result = post_soap(gw, "<ws/>", capability=SoapCapability.SEARCH, soap_action="searchProcurements")
    assert result.status in (TransportStatus.AVAILABLE, TransportStatus.GATEWAY_ONLY)