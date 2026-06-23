import pytest
from urllib.parse import unquote

from src.modules.tender_operator_agent_demo.procurement_discovery import (
    build_public_search_url,
    list_procurement_sources,
    search_procurements,
)
from src.modules.tender_operator_agent_demo.procurement_schemas import ProcurementSearchRequest
from src.modules.tender_operator_agent_demo.settings import clear_zakupki_soap_settings_cache


def test_demo_local_procurement_search_returns_results(client):
    response = client.get(
        "/api/demo/tender-agent/procurements/search",
        params={"query": "электротехническое оборудование", "source": "demo_local", "max_results": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "demo_local"
    assert payload["results"]
    first = payload["results"][0]
    assert first["procurement_id"]
    assert first["title"]
    assert first["customer_name"] == "Промышленный заказчик"
    assert first["attachments_status"] in {
        "downloadable",
        "manual_upload_required",
        "unavailable_in_demo",
        "source_requires_authorization",
    }
    assert payload["sources"]


def test_unknown_procurement_source_is_rejected(client):
    response = client.get(
        "/api/demo/tender-agent/procurements/search",
        params={"query": "кабель", "source": "unknown_source"},
    )

    assert response.status_code == 400
    assert "Unknown procurement source" in response.json()["detail"]


def test_disabled_procurement_source_returns_warning(client):
    response = client.get(
        "/api/demo/tender-agent/procurements/search",
        params={"query": "кабель", "source": "public_eis_html_44fz"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"] == []
    assert payload["warnings"]


def test_procurement_sources_include_zakupki_disabled_without_token(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", raising=False)
    clear_zakupki_soap_settings_cache()

    sources = {item.source: item for item in list_procurement_sources()}

    assert sources["demo_local"].configured is True
    assert sources["public_eis_html_44fz"].configured is True
    assert sources["zakupki_gov_ru_getdocs_ip"].configured is False
    assert "ZAKUPKI_GOV_RU_SOAP_TOKEN" in (sources["zakupki_gov_ru_getdocs_ip"].reason or "")


def test_procurement_discovery_request_schema_searches_demo_local():
    results = search_procurements(
        ProcurementSearchRequest(source="demo_local", query="кабель", max_results=3)
    )

    assert results
    assert results[0].notice_number
    assert results[0].source == "demo_local"
    assert results[0].attachments_count >= 0


def test_procurement_discovery_unknown_source_rejected_directly():
    with pytest.raises(ValueError, match="Unknown procurement source"):
        search_procurements(ProcurementSearchRequest(source="unknown_source", query="кабель"))


def test_public_search_url_is_built_for_44fz():
    payload = build_public_search_url(query="кабель", law="44fz", region="77")

    assert payload.source == "public_eis_html_44fz"
    assert "extendedsearch" in payload.eis_search_url
    assert "кабель" in unquote(payload.eis_search_url)
    assert payload.note


def test_getdocs_source_returns_empty_results_in_search_mode():
    results = search_procurements(ProcurementSearchRequest(source="zakupki_gov_ru_getdocs_ip", query="кабель"))

    assert results == []
