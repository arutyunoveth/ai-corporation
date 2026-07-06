import pytest
from datetime import date
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
    with pytest.raises(RuntimeError, match="не настроен|не поддерживает keyword search"):
        search_procurements(ProcurementSearchRequest(source="zakupki_gov_ru_getdocs_ip", query="кабель"))


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


def test_public_44fz_filter_helper_drops_expired_submission_status(monkeypatch):
    import src.modules.tender_operator_agent_demo.procurement_discovery as discovery

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 7, 6)

    monkeypatch.setattr(discovery, "date", FixedDate)

    cards = [
        {
            "title": "Просроченная закупка",
            "status": "Подача заявок",
            "procedure_type": "Электронный аукцион",
            "publication_date": "01.07.2026",
            "deadline": "05.07.2026",
            "initial_price": 1000000.0,
        },
        {
            "title": "Актуальная закупка",
            "status": "Подача заявок",
            "procedure_type": "Электронный аукцион",
            "publication_date": "01.07.2026",
            "deadline": "07.07.2026",
            "initial_price": 1000000.0,
        },
    ]

    filtered = _filter_public_44fz_cards(cards)

    assert [card["title"] for card in filtered] == ["Актуальная закупка"]


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


def test_public_44fz_search_returns_success_empty_after_post_filters(monkeypatch):
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
                "status": "Закупка завершена",
                "procedure_type": "Запрос котировок",
                "source_url": "https://zakupki.gov.ru/epz/order/notice/zk20/view/common-info.html?regNumber=1",
                "law": "44fz",
                "warnings": [],
            },
        ],
    )

    result = search_public_44fz(
        query="тест",
        law="44fz",
        procedure_type="Электронный аукцион",
        max_results=5,
    )

    assert result["status"] == "empty_results"
    assert result["outcome"] == "success_empty"
    assert result["cards"] == []
    assert "не найдены" in result["message"]


def test_public_44fz_search_returns_source_unavailable_for_js_heavy(monkeypatch):
    import src.modules.tender_operator_agent_demo.procurement_discovery as discovery

    monkeypatch.setattr(
        discovery,
        "fetch_public_44fz_search_page",
        lambda url: {"status": "js_heavy", "html": None, "error": None},
    )

    result = search_public_44fz(query="тест", law="44fz")

    assert result["status"] == "js_heavy"
    assert result["outcome"] == "source_unavailable"
    assert result["cards"] == []
    assert "недоступен" in result["message"]


def test_public_44fz_search_returns_validation_error_for_empty_query():
    result = search_public_44fz(query="", law="44fz")

    assert result["status"] == "validation_error"
    assert result["outcome"] == "validation_error"
    assert result["cards"] == []
    assert result["error"]


def test_public_44fz_search_returns_pagination_fields_and_date_desc(monkeypatch):
    import src.modules.tender_operator_agent_demo.procurement_discovery as discovery

    monkeypatch.setattr(
        discovery,
        "fetch_public_44fz_search_page",
        lambda url: {
            "status": "parsed",
            "html": '<div class="search-results__total">24 записи</div>',
            "error": None,
        },
    )
    monkeypatch.setattr(
        discovery,
        "parse_44fz_search_results",
        lambda html: [
            {
                "title": "Старая закупка",
                "notice_number": "1",
                "reestr_number": "1",
                "customer_name": "Заказчик",
                "initial_price": 1000.0,
                "publication_date": "01.07.2026",
                "deadline": "10.07.2026",
                "status": "Подача заявок",
                "procedure_type": "Электронный аукцион",
                "source_url": "https://zakupki.gov.ru/1",
                "law": "44fz",
                "warnings": [],
            },
            {
                "title": "Новая закупка",
                "notice_number": "2",
                "reestr_number": "2",
                "customer_name": "Заказчик",
                "initial_price": 2000.0,
                "publication_date": "06.07.2026",
                "deadline": "12.07.2026",
                "status": "Подача заявок",
                "procedure_type": "Электронный аукцион",
                "source_url": "https://zakupki.gov.ru/2",
                "law": "44fz",
                "warnings": [],
            },
        ],
    )

    result = search_public_44fz(query="тест", law="44fz", page=2, page_size=10, max_results=10)

    assert result["page"] == 2
    assert result["page_size"] == 10
    assert result["returned_count"] == 2
    assert result["total_count"] == 24
    assert result["has_more"] is True
    assert result["next_page"] == 3
    assert result["sort"] == "publication_date_desc"
    assert result["message"] == "Показаны карточки 11–12 из 24."
    assert [card["notice_number"] for card in result["cards"]] == ["2", "1"]


def test_public_44fz_search_pushes_status_filter_to_eis_and_keeps_exact_total(monkeypatch):
    import src.modules.tender_operator_agent_demo.procurement_discovery as discovery

    captured: dict[str, str] = {}

    def fake_fetch(url: str):
        captured["url"] = url
        return {
            "status": "parsed",
            "html": '<a onclick="downloadCsv(\'?searchString=test\', \'12\')"></a>',
            "error": None,
        }

    monkeypatch.setattr(discovery, "fetch_public_44fz_search_page", fake_fetch)
    monkeypatch.setattr(
        discovery,
        "parse_44fz_search_results",
        lambda html: [
            {
                "title": "Закупка",
                "notice_number": "1",
                "reestr_number": "1",
                "customer_name": "Заказчик",
                "initial_price": 1000.0,
                "publication_date": "06.07.2026",
                "deadline": "12.07.2026",
                "status": "Определение поставщика завершено",
                "procedure_type": "Электронный аукцион",
                "source_url": "https://zakupki.gov.ru/1",
                "law": "44fz",
                "warnings": [],
            },
        ],
    )

    result = search_public_44fz(
        query="тест",
        law="44fz",
        status_filter="Закупка завершена",
        page=1,
        page_size=10,
        max_results=10,
    )

    assert "pc=on" in captured["url"]
    assert result["total_count"] == 12
    assert result["returned_count"] == 1
    assert result["message"] == "Показаны первые 1 карточек из 12."
    assert result["cards"][0]["notice_number"] == "1"


def test_public_44fz_search_drops_exact_total_for_non_native_filters(monkeypatch):
    import src.modules.tender_operator_agent_demo.procurement_discovery as discovery

    monkeypatch.setattr(
        discovery,
        "fetch_public_44fz_search_page",
        lambda url: {
            "status": "parsed",
            "html": '<a onclick="downloadCsv(\'?searchString=test\', \'99\')"></a>',
            "error": None,
        },
    )
    monkeypatch.setattr(
        discovery,
        "parse_44fz_search_results",
        lambda html: [
            {
                "title": "Закупка",
                "notice_number": "1",
                "reestr_number": "1",
                "customer_name": "Заказчик",
                "initial_price": 1000.0,
                "publication_date": "06.07.2026",
                "deadline": "12.07.2026",
                "status": "Подача заявок",
                "procedure_type": "Электронный аукцион",
                "source_url": "https://zakupki.gov.ru/1",
                "law": "44fz",
                "warnings": [],
            },
        ],
    )

    result = search_public_44fz(query="тест", law="44fz", procedure_type="Электронный аукцион", page=1, page_size=10, max_results=10)

    assert result["total_count"] is None
    assert result["message"] == "Показаны 1 карточек на странице 1."
