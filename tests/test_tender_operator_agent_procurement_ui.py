from src.modules.tender_operator_agent_demo.settings import clear_zakupki_soap_settings_cache


def test_procurement_search_tab_is_first(client):
    response = client.get("/demo/tender-agent")

    assert response.status_code == 200
    text = response.text
    assert text.index("Найти закупку") < text.index("Загрузить документы") < text.index("Демо-набор")
    assert "Поиск работает в безопасном read-only режиме" in text


def test_procurement_sources_endpoint_returns_demo_and_zakupki_disabled_without_token(client, monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", raising=False)
    clear_zakupki_soap_settings_cache()

    response = client.get("/api/demo/tender-agent/procurement/sources")

    assert response.status_code == 200
    sources = {item["source"]: item for item in response.json()}
    assert sources["demo_local"]["configured"] is True
    assert sources["zakupki_gov_ru_soap"]["configured"] is False
    assert "ZAKUPKI_GOV_RU_SOAP_TOKEN" in sources["zakupki_gov_ru_soap"]["reason"]


def test_procurement_page_does_not_render_token(client, monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "secret-token-value")
    clear_zakupki_soap_settings_cache()

    response = client.get("/demo/tender-agent")

    assert response.status_code == 200
    assert "secret-token-value" not in response.text


def test_procurement_search_post_returns_demo_cards(client):
    response = client.post(
        "/api/demo/tender-agent/procurement/search",
        json={"source": "demo_local", "query": "электротехническое оборудование", "max_results": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]["source"] == "demo_local"
    assert payload[0]["notice_number"]
    assert "can_download_attachments" in payload[0]


def test_procurement_search_post_rejects_unknown_source(client):
    response = client.post(
        "/api/demo/tender-agent/procurement/search",
        json={"source": "unknown_source", "query": "кабель"},
    )

    assert response.status_code == 400
    assert "Unknown procurement source" in response.json()["detail"]
