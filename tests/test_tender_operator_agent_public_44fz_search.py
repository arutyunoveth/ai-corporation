from src.modules.tender_operator_agent_demo.public_44fz_search import (
    ALLOWED_44FZ_HOSTS,
    EIS_44FZ_SEARCH_PATH,
    build_44fz_search_url,
    build_public_eis_search_url,
    normalize_44fz_search_params,
    normalize_public_eis_law,
    resolve_public_eis_stage_flag,
    validate_public_eis_url,
)


def test_build_search_url_encodes_russian_query():
    url = build_44fz_search_url("электротехническое оборудование")
    assert url.startswith("https://zakupki.gov.ru/epz/order/extendedsearch/results.html?")
    assert "searchString=%D1%8D%D0%BB%D0%B5%D0%BA%D1%82%D1%80%D0%BE%D1%82%D0%B5%D1%85%D0%BD%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%BE%D0%B5" in url
    assert "morphology=on" in url
    assert "fz44=on" in url


def test_build_search_url_supports_223fz_and_capital_repair():
    url_223 = build_public_eis_search_url("обучение", law="223fz")
    url_caprepair = build_public_eis_search_url("ремонт", law="capital_repair")

    assert "fz223=on" in url_223
    assert "ppRf615=on" in url_caprepair


def test_build_search_url_host_is_zakupki_gov_ru():
    url = build_44fz_search_url("кабель")
    assert url.startswith("https://zakupki.gov.ru/")
    assert "zakupki.gov.ru" in url


def test_build_search_url_with_all_params():
    url = build_44fz_search_url(
        query="шкаф",
        region="Москва",
        date_from="2026-01-01",
        date_to="2026-06-30",
        price_from=1000000,
        price_to=5000000,
        page=2,
        max_results=20,
    )
    assert "priceFromGeneral=1000000" in url
    assert "priceToGeneral=5000000" in url
    assert "publishDateFrom=01.01.2026" in url
    assert "publishDateTo=30.06.2026" in url
    assert "region=%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0" in url
    assert "pageNumber=2" in url
    assert "recordsPerPage=20" in url


def test_build_search_url_includes_stage_flag():
    url = build_public_eis_search_url("электротех", law="44fz", status_filter="Подача заявок", max_results=10)

    assert "af=on" in url


def test_resolve_public_eis_stage_flag_maps_known_values():
    assert resolve_public_eis_stage_flag("Подача заявок") == "af"
    assert resolve_public_eis_stage_flag("Работа комиссии") == "ca"
    assert resolve_public_eis_stage_flag("Закупка завершена") == "pc"


def test_build_search_url_normalizes_iso_dates_for_eis():
    url = build_public_eis_search_url("электротех", date_from="2026-07-01", date_to="2026-07-06")

    assert "publishDateFrom=01.07.2026" in url
    assert "publishDateTo=06.07.2026" in url


def test_build_search_url_rejects_empty_query():
    try:
        build_44fz_search_url("")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Поисковый запрос не может быть пустым" in str(exc)


def test_normalize_public_eis_law_accepts_russian_names():
    assert normalize_public_eis_law("44-ФЗ") == "44fz"
    assert normalize_public_eis_law("223-ФЗ") == "223fz"
    assert normalize_public_eis_law("капремонт") == "capital_repair"


def test_validate_public_eis_url_valid():
    url = build_44fz_search_url("тест")
    assert validate_public_eis_url(url) is True


def test_validate_public_eis_url_rejects_unsupported_host():
    assert validate_public_eis_url("https://example.com/search") is False


def test_validate_public_eis_url_rejects_invalid_scheme():
    assert validate_public_eis_url("ftp://zakupki.gov.ru/search") is False


def test_validate_public_eis_url_rejects_empty():
    assert validate_public_eis_url("") is False


def test_validate_public_eis_url_rejects_wrong_path():
    url = "https://zakupki.gov.ru/some/other/path"
    assert validate_public_eis_url(url) is False


def test_normalize_params_requires_query():
    try:
        normalize_44fz_search_params(query=None)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Поисковый запрос не может быть пустым" in str(exc)


def test_normalize_params_with_all():
    params = normalize_44fz_search_params(
        query="тест",
        region="СПб",
        date_from="2026-01-01",
        price_from=1000.0,
        page=3,
        max_results=5,
    )
    assert params["searchString"] == "тест"
    assert params["region"] == "СПб"
    assert params["publishDateFrom"] == "01.01.2026"
    assert params["priceFromGeneral"] == "1000.0"
    assert params["pageNumber"] == "3"
    assert params["recordsPerPage"] == "5"


def test_build_search_url_max_results_clamped():
    url = build_44fz_search_url("тест", max_results=100)
    assert "recordsPerPage=50" in url


def test_build_search_url_max_results_minimum():
    url = build_44fz_search_url("тест", max_results=0)
    assert "recordsPerPage=1" in url


def test_source_urls_available(client):
    response = client.get("/api/demo/tender-agent/procurement/sources")
    assert response.status_code == 200
    sources = {item["source"]: item for item in response.json()}
    assert "public_eis_html_44fz" in sources
    assert sources["public_eis_html_44fz"]["enabled"] is True


def test_ui_contains_public_44fz_source_label(client):
    response = client.get("/demo/tender-agent")
    assert response.status_code == 200
    assert "Публичный поиск ЕИС 44-ФЗ" in response.text
    assert "Без обхода captcha" in response.text
    assert "Только чтение" in response.text
    assert "Без подачи на площадку" in response.text


def test_ui_search_results_handoff_flow_text(client):
    response = client.get("/demo/tender-agent")
    assert response.status_code == 200
    assert "Получить документацию и анализировать" in response.text or "Поиск закупки" in response.text
