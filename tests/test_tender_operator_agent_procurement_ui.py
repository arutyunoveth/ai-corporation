from src.modules.tender_operator_agent_demo.settings import clear_zakupki_soap_settings_cache


def test_procurement_search_tab_is_first(client):
    response = client.get("/demo/tender-agent")

    assert response.status_code == 200
    text = response.text
    assert text.index("Найти закупку") < text.index("Получить документацию по номеру") < text.index("Загрузить документы") < text.index("Демо-набор")
    assert "Поиск работает в безопасном read-only режиме" in text
    assert "Диагностика ЕИС" in text
    assert "Токен выпущен как физическое лицо" in text
    assert "Источник закупки" in text
    assert "Журнал работы агента" in text


def test_procurement_sources_endpoint_returns_demo_and_zakupki_disabled_without_token(client, monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", raising=False)
    clear_zakupki_soap_settings_cache()

    response = client.get("/api/demo/tender-agent/procurement/sources")

    assert response.status_code == 200
    sources = {item["source"]: item for item in response.json()}
    assert sources["demo_local"]["configured"] is True
    assert sources["public_eis_html_44fz"]["configured"] is True
    assert sources["zakupki_gov_ru_getdocs_ip"]["configured"] is False
    assert "ZAKUPKI_GOV_RU_SOAP_TOKEN" in sources["zakupki_gov_ru_getdocs_ip"]["reason"]


def test_procurement_page_does_not_render_token(client, monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "secret-token-value")
    clear_zakupki_soap_settings_cache()

    response = client.get("/demo/tender-agent")

    assert response.status_code == 200
    assert "secret-token-value" not in response.text


def test_procurement_sources_endpoint_returns_safe_live_diagnostics(client, monkeypatch, tmp_path):
    diagnostics_dir = tmp_path / "soap_diagnostics"
    diagnostics_dir.mkdir()
    (diagnostics_dir / "last_status.json").write_text(
        '{"configured": true, "token_present": true, "token_owner": "individual", "endpoint_host": "int44.zakupki.gov.ru", "endpoint_path": "/eis-integration/services/getDocsIP", "last_status": "error", "last_error": "Connection reset by peer", "method_name": "getDocsByReestrNumberRequest"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_CORP_ZAKUPKI_SOAP_DIAGNOSTICS_DIR", str(diagnostics_dir))
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_ENABLED", "1")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "test-token-value-not-real")
    clear_zakupki_soap_settings_cache()

    response = client.get("/api/demo/tender-agent/procurement/sources")

    assert response.status_code == 200
    payload = {item["source"]: item for item in response.json()}
    diagnostics = payload["zakupki_gov_ru_getdocs_ip"]["safe_diagnostics"]
    assert payload["zakupki_gov_ru_getdocs_ip"]["configured"] is True
    assert diagnostics["token_present"] is True
    assert diagnostics["endpoint_host"] == "int44.zakupki.gov.ru"
    assert diagnostics["endpoint_path"] == "/eis-integration/services/getDocsIP"
    assert diagnostics["last_error"] == "Connection reset by peer"
    assert diagnostics["token_owner"] == "individual"


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


def test_procurement_ui_contains_getdocs_tab(client):
    response = client.get("/demo/tender-agent")

    assert response.status_code == 200
    assert "Получить документацию по номеру" in response.text
    assert "Получить документацию из ЕИС" in response.text
    assert "Запустить анализ после скачивания" in response.text
    assert "Результат получения документации" in response.text
