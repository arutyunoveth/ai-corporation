import pytest
from urllib.parse import unquote

from src.modules.tender_operator_agent_demo.procurement_discovery import (
    _filter_public_44fz_cards,
    build_public_search_url,
    list_procurement_sources,
    search_public_44fz,
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
    monkeypatch.setattr("src.modules.tender_operator_agent_demo.settings._seed_env_from_local_files", lambda: None)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", raising=False)
    clear_zakupki_soap_settings_cache()

    sources = {item.source: item for item in list_procurement_sources()}

    assert sources["demo_local"].configured is True
    assert sources["public_eis_html_44fz"].configured is True
    assert sources["public_eis_html_capital_repair"].configured is True
    assert sources["zakupki_gov_ru_getdocs_ip"].configured is False
    assert "не настроен" in (sources["zakupki_gov_ru_getdocs_ip"].reason or "")


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


def test_public_search_url_is_built_for_capital_repair():
    payload = build_public_search_url(query="ремонт", law="capital_repair")

    assert payload.source == "public_eis_html_capital_repair"
    assert "ppRf615=on" in payload.eis_search_url


def test_getdocs_source_returns_empty_results_in_search_mode():
    results = search_procurements(ProcurementSearchRequest(source="zakupki_gov_ru_getdocs_ip", query="кабель"))

    assert results == []


def test_public_44fz_filter_helper_applies_status_procedure_and_deadline():
    cards = [
        {
            "title": "Закупка 1",
            "status": "Подача заявок",
            "procedure_type": "Электронный аукцион",
            "publication_date": "01.07.2026",
            "deadline": "10.07.2026",
            "initial_price": 1000000.0,
        },
        {
            "title": "Закупка 2",
            "status": "Закупка завершена",
            "procedure_type": "Запрос котировок",
            "publication_date": "20.06.2026",
            "deadline": "25.06.2026",
            "initial_price": 500000.0,
        },
    ]

    filtered = _filter_public_44fz_cards(
        cards,
        status_filter="Подача заявок",
        procedure_type="Электронный аукцион",
        deadline_from="2026-07-01",
        deadline_to="2026-07-15",
    )

    assert len(filtered) == 1
    assert filtered[0]["title"] == "Закупка 1"


def test_public_44fz_search_uses_post_filters(monkeypatch):
    import src.modules.tender_operator_agent_demo.procurement_discovery as discovery

    monkeypatch.setattr(
        discovery,
        "fetch_public_44fz_search_page",
        lambda url: {"status": "parsed", "html": "<html></html>", "error": None},
    )
    monkeypatch.setattr(
        discovery,
        "parse_44fz_search_results",
        lambda html: [
            {
                "title": "Закупка 1",
                "notice_number": "1",
                "reestr_number": "1",
                "customer_name": "Заказчик",
                "initial_price": 1000000.0,
                "publication_date": "01.07.2026",
                "deadline": "10.07.2026",
                "status": "Подача заявок",
                "procedure_type": "Электронный аукцион",
                "source_url": "https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber=1",
                "law": "44fz",
                "warnings": [],
            },
            {
                "title": "Закупка 2",
                "notice_number": "2",
                "reestr_number": "2",
                "customer_name": "Заказчик",
                "initial_price": 1000000.0,
                "publication_date": "01.07.2026",
                "deadline": "10.07.2026",
                "status": "Закупка завершена",
                "procedure_type": "Запрос котировок",
                "source_url": "https://zakupki.gov.ru/epz/order/notice/zk20/view/common-info.html?regNumber=2",
                "law": "44fz",
                "warnings": [],
            },
        ],
    )

    result = search_public_44fz(
        query="тест",
        law="223fz",
        status_filter="Подача заявок",
        procedure_type="Электронный аукцион",
        deadline_from="2026-07-01",
        deadline_to="2026-07-15",
        max_results=5,
    )

    assert result["status"] == "parsed"
    assert len(result["cards"]) == 1
    assert result["cards"][0]["notice_number"] == "1"
    assert result["cards"][0]["law"] == "223fz"
    assert result["cards"][0]["source"] == "public_eis_html_223fz"
