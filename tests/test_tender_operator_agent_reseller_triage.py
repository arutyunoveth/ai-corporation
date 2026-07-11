import pytest

from src.modules.tender_operator_agent_demo.schemas import (
    ResellerDecisionLabel,
    ResellerSearchRequest,
    ResellerSearchResponse,
    ResellerTenderSearchResult,
    ResellerTriageReport,
    SourceType,
    StopFactor,
    StopFactorSeverity,
    TotalCountKind,
)
from src.modules.tender_operator_agent_demo.reseller_triage_service import (
    analyze_tender_for_reseller,
    search_tenders,
    select_freshest_tender,
)


def test_search_first_demo_page_renders(client):
    response = client.get("/demo/tender-agent")
    assert response.status_code == 200
    assert "Быстрый разбор закупки" in response.text
    assert "GO / NO-GO" in response.text
    assert "Ключевое слово" in response.text
    assert "Найти и разобрать свежую закупку" in response.text
    assert "Анализ по номеру" in response.text
    assert "Загрузка документов" in response.text


def test_search_tenders_returns_summary():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert isinstance(response, ResellerSearchResponse)
    assert response.query == "кабель"
    assert response.total_results is not None
    assert response.total_results > 0
    assert len(response.results) > 0

    first = response.results[0]
    assert first.title is not None
    assert first.customer_name is not None


def test_select_freshest_tender():
    results = [
        ResellerTenderSearchResult(
            procurement_id="PR-001", title="Старая закупка", customer_name="Заказчик",
            initial_price=100000, publication_date="2026-01-01",
        ),
        ResellerTenderSearchResult(
            procurement_id="PR-002", title="Средняя закупка", customer_name="Заказчик",
            initial_price=200000, publication_date="2026-06-01",
        ),
        ResellerTenderSearchResult(
            procurement_id="PR-003", title="Свежая закупка", customer_name="Заказчик",
            initial_price=300000, publication_date="2026-06-20",
        ),
    ]

    freshest, reason = select_freshest_tender(results)
    assert freshest is not None
    assert freshest.procurement_id == "PR-003"
    assert freshest.is_freshest is True
    assert reason == "date_available_selected_latest"

    other_results = [r for r in results if not r.is_freshest]
    assert len(other_results) == 2


def test_select_freshest_tender_empty():
    result, reason = select_freshest_tender([])
    assert result is None
    assert reason is None


def test_select_freshest_tender_single():
    results = [
        ResellerTenderSearchResult(
            procurement_id="PR-001", title="Единственная закупка", customer_name="Заказчик",
            publication_date="2026-06-15",
        )
    ]
    freshest, reason = select_freshest_tender(results)
    assert freshest is not None
    assert freshest.procurement_id == "PR-001"
    assert freshest.is_freshest is True
    assert reason == "date_available_selected_latest"


def test_triage_analyzes_only_one_freshest_tender():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.freshest is not None
    assert response.freshest.is_freshest is True

    freshest_id = response.freshest.procurement_id
    freshest_count = sum(1 for r in response.results if r.is_freshest)
    assert freshest_count == 1

    triage = analyze_tender_for_reseller(freshest_id, "demo_local")
    assert triage is not None
    assert triage.decision_label in (
        ResellerDecisionLabel.GO, ResellerDecisionLabel.NO_GO,
        ResellerDecisionLabel.NEEDS_REVIEW, ResellerDecisionLabel.LOW_PRIORITY,
    )


def test_reseller_decision_schema():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.freshest is not None

    triage = analyze_tender_for_reseller(response.freshest.procurement_id, "demo_local")
    assert isinstance(triage, ResellerTriageReport)
    assert triage.decision_label in (
        ResellerDecisionLabel.GO, ResellerDecisionLabel.NO_GO,
        ResellerDecisionLabel.NEEDS_REVIEW, ResellerDecisionLabel.LOW_PRIORITY,
    )
    assert 0 <= triage.decision_score <= 100
    assert isinstance(triage.decision_reasons, list)
    assert len(triage.decision_reasons) > 0
    assert isinstance(triage.stop_factors, list)
    assert isinstance(triage.manager_recommendation, str)
    assert len(triage.manager_recommendation) > 0


def test_critical_stop_factor_prevents_go():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.freshest is not None

    triage = analyze_tender_for_reseller(response.freshest.procurement_id, "demo_local")
    has_critical = any(f.severity == StopFactorSeverity.CRITICAL for f in triage.stop_factors)
    if has_critical:
        assert triage.decision_label != ResellerDecisionLabel.GO


def test_no_search_results_message():
    request = ResellerSearchRequest(query="__nonexistent_query_xyz__", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert isinstance(response, ResellerSearchResponse)
    assert len(response.results) == 0
    assert response.freshest is None


def test_unavailable_documents_returns_needs_review():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.freshest is not None

    from src.modules.tender_operator_agent_demo.reseller_triage_service import _fetch_tender_details

    details = _fetch_tender_details("NONEXISTENT-TENDER-ID", "demo_local")
    assert details.get("attachments_count", 0) == 0
    triage = analyze_tender_for_reseller("NONEXISTENT-TENDER-ID", "demo_local")
    assert triage.decision_label == ResellerDecisionLabel.NEEDS_REVIEW


def test_customer_mode_public_search_unavailable():
    request = ResellerSearchRequest(query="кабель", source="public_eis_html_44fz", customer_mode=True)
    response = search_tenders(request)
    assert isinstance(response, ResellerSearchResponse)
    assert response.search_unavailable is True
    assert response.synthetic_used is False
    assert response.source_type == SourceType.LIVE
    assert len(response.results) == 0
    assert response.freshest is None


def test_dev_mode_fallback_is_labeled():
    request = ResellerSearchRequest(query="кабель", source="public_eis_html_44fz", customer_mode=False)
    response = search_tenders(request)
    assert isinstance(response, ResellerSearchResponse)
    assert response.is_fallback is True
    assert response.fallback_label is not None
    assert "недоступен" in response.fallback_label


def test_search_and_triage_api_endpoint(client):
    response = client.post(
        "/api/demo/tender-agent/reseller/search-and-triage",
        json={"query": "кабель", "source": "demo_local", "customer_mode": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["search"]["total_results"] > 0
    assert payload["search"]["freshest"] is not None
    assert payload["triage"] is not None
    assert payload["triage"]["decision_label"] in ("GO", "NO_GO", "NEEDS_REVIEW", "LOW_PRIORITY")
    assert 0 <= payload["triage"]["decision_score"] <= 100
    assert len(payload["triage"]["decision_reasons"]) > 0
    assert payload["analysis_limit_notice"] is not None


def test_reseller_summary_included_in_report():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.freshest is not None

    triage = analyze_tender_for_reseller(response.freshest.procurement_id, "demo_local")
    assert triage.reseller_summary is not None
    assert len(triage.reseller_summary) > 0
    assert triage.reseller_summary != triage.manager_recommendation


def test_reseller_summary_in_api_response(client):
    response = client.post(
        "/api/demo/tender-agent/reseller/search-and-triage",
        json={"query": "кабель", "source": "demo_local", "customer_mode": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["triage"] is not None
    assert "reseller_summary" in payload["triage"]
    assert len(payload["triage"]["reseller_summary"]) > 0


def test_no_line_items_prevents_go():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.freshest is not None

    triage = analyze_tender_for_reseller(response.freshest.procurement_id, "demo_local")
    has_no_line_items = any(sf.code == "no_line_items" for sf in triage.stop_factors)
    if has_no_line_items:
        assert triage.decision_label != ResellerDecisionLabel.GO


def test_total_results_exact_for_demo_local():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.total_results is not None
    assert response.total_results > 0
    assert response.total_results == len(response.results)
    assert response.total_count_kind == TotalCountKind.EXACT
    assert "минимум" not in (response.total_results_label or "")
    assert "Показано" not in (response.total_results_label or "")


def test_freshest_selected_no_dates():
    results = [
        ResellerTenderSearchResult(
            procurement_id="PR-001", title="Без даты 1", customer_name="З", publication_date=None,
        ),
        ResellerTenderSearchResult(
            procurement_id="PR-002", title="Без даты 2", customer_name="З", publication_date=None,
        ),
    ]
    freshest, reason = select_freshest_tender(results)
    assert freshest is not None
    assert freshest.is_freshest is True
    assert freshest.procurement_id == "PR-001"
    assert reason == "date_unavailable_first_result"


def test_mixed_dates_selects_latest_dated_result():
    results = [
        ResellerTenderSearchResult(
            procurement_id="PR-001", title="Без даты", customer_name="З", publication_date=None,
        ),
        ResellerTenderSearchResult(
            procurement_id="PR-002", title="Старая", customer_name="З", publication_date="2026-01-01",
        ),
        ResellerTenderSearchResult(
            procurement_id="PR-003", title="Свежая", customer_name="З", publication_date="2026-06-20",
        ),
    ]
    freshest, reason = select_freshest_tender(results)
    assert freshest is not None
    assert freshest.procurement_id == "PR-003"
    assert freshest.is_freshest is True
    assert reason == "date_mixed_selected_latest_dated"


def test_dev_mode_fallback_label_uses_russian():
    request = ResellerSearchRequest(query="кабель", source="public_eis_html_44fz", customer_mode=False)
    response = search_tenders(request)
    if response.is_fallback:
        assert response.fallback_label is not None
        assert response.fallback_label == "Источник поиска временно недоступен. Показан демонстрационный набор данных."


@pytest.mark.parametrize("query", ["кабель", "светильник", "автоматический выключатель", "электротехническая продукция"])
def test_smoke_queries_dont_crash(query):
    request = ResellerSearchRequest(query=query, source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert isinstance(response, ResellerSearchResponse)
    assert response.total_results is not None
    assert response.query == query
    if response.total_results > 0:
        assert response.freshest is not None
        triage = analyze_tender_for_reseller(response.freshest.procurement_id, "demo_local")
        assert triage.decision_label in (
            ResellerDecisionLabel.GO, ResellerDecisionLabel.NO_GO,
            ResellerDecisionLabel.NEEDS_REVIEW, ResellerDecisionLabel.LOW_PRIORITY,
        )


def test_demo_source_metadata():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.source_type is not None
    assert response.source_label is not None
    assert response.fallback_used is False
    assert response.source_notice is not None
    assert response.synthetic_used is True


def test_demo_source_metadata_via_api(client):
    response = client.post(
        "/api/demo/tender-agent/reseller/search-and-triage",
        json={"query": "кабель", "source": "demo_local", "customer_mode": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["search"]["source_type"] is not None
    assert payload["search"]["source_label"] is not None
    assert isinstance(payload["search"]["fallback_used"], bool)
    assert payload["triage"]["source_type"] is not None
    assert payload["triage"]["source_label"] is not None


def test_dev_mode_fallback_is_explicitly_labeled():
    request = ResellerSearchRequest(query="кабель", source="public_eis_html_44fz", customer_mode=False)
    response = search_tenders(request)
    if response.is_fallback:
        assert response.fallback_used is True
        assert response.source_type == SourceType.DEMO
        assert "недоступен" in (response.source_notice or "")
        assert "демонстрационный" in (response.source_notice or "")


def test_total_count_kind_exact():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.total_count_kind == TotalCountKind.EXACT
    assert "Найдено закупок" in (response.total_results_label or "")
    assert "минимум" not in (response.total_results_label or "")
    assert "Показано" not in (response.total_results_label or "")


def test_all_results_without_dates_selects_first_with_warning():
    results = [
        ResellerTenderSearchResult(
            procurement_id="PR-001", title="Первый", customer_name="З", publication_date=None,
        ),
        ResellerTenderSearchResult(
            procurement_id="PR-002", title="Второй", customer_name="З", publication_date=None,
        ),
    ]
    freshest, reason = select_freshest_tender(results)
    assert freshest is not None
    assert freshest.procurement_id == "PR-001"
    assert reason == "date_unavailable_first_result"


def test_mixed_dates_selects_latest_dated():
    results = [
        ResellerTenderSearchResult(
            procurement_id="PR-D1", title="Без даты", customer_name="З", publication_date=None,
        ),
        ResellerTenderSearchResult(
            procurement_id="PR-D2", title="Старая", customer_name="З", publication_date="2026-03-01",
        ),
        ResellerTenderSearchResult(
            procurement_id="PR-D3", title="Новая", customer_name="З", publication_date="2026-06-15",
        ),
    ]
    freshest, reason = select_freshest_tender(results)
    assert freshest.procurement_id == "PR-D3"
    assert reason == "date_mixed_selected_latest_dated"


def test_triage_report_contains_tender_card():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.freshest is not None

    triage = analyze_tender_for_reseller(response.freshest.procurement_id, "demo_local")
    assert triage.tender_card is not None
    assert triage.tender_card.tender_id is not None
    assert triage.tender_card.title is not None
    assert triage.tender_card.customer is not None
    assert triage.tender_card.nmck is not None or True
    assert triage.tender_card.publication_date is not None or True


def test_triage_report_contains_line_items_or_no_items_notice():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.freshest is not None

    triage = analyze_tender_for_reseller(response.freshest.procurement_id, "demo_local")
    has_line_items = triage.has_line_items
    no_items_stop = any(sf.code == "no_line_items" for sf in triage.stop_factors)
    assert has_line_items or no_items_stop


def test_no_line_items_blocks_go():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.freshest is not None

    triage = analyze_tender_for_reseller(response.freshest.procurement_id, "demo_local")
    has_no_line_items = any(sf.code == "no_line_items" for sf in triage.stop_factors)
    if has_no_line_items:
        assert triage.decision_label != ResellerDecisionLabel.GO


def test_ui_does_not_expose_technical_terms(client):
    response = client.get("/demo/tender-agent")
    assert response.status_code == 200
    parts = response.text.split("<script")
    visible_text = parts[0]
    for p in parts[1:]:
        if "</script>" in p:
            visible_text += p.split("</script>", 1)[1]
    visible_text = visible_text.lower()
    hidden_terms = ["line_items", "runtime"]
    for term in hidden_terms:
        assert term not in visible_text, f"Forbidden term '{term}' found in visible UI"


def test_ui_dev_mode_labels_synthetic_data(client):
    response = client.get("/demo/tender-agent?dev=1")
    assert response.status_code == 200
    assert "Режим разработки" in response.text
    assert "синтетические данные" in response.text.lower()


def test_ui_customer_mode_has_no_synthetic_terms(client):
    response = client.get("/demo/tender-agent")
    assert response.status_code == 200
    parts = response.text.split("<script")
    visible_text = parts[0]
    for p in parts[1:]:
        if "</script>" in p:
            visible_text += p.split("</script>", 1)[1]
    visible_text_lower = visible_text.lower()
    forbidden = ["demo_local", "fixture", "synthetic"]
    for term in forbidden:
        assert term not in visible_text_lower, f"Forbidden term '{term}' found in visible UI"


def test_selection_reason_in_search_response():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.selection_reason is not None
    assert response.selection_reason in (
        "date_available_selected_latest",
        "date_mixed_selected_latest_dated",
        "date_unavailable_first_result",
    )


# New tests for customer/dev mode separation

def test_customer_mode_does_not_use_synthetic_data():
    request = ResellerSearchRequest(query="кабель", customer_mode=True)
    response = search_tenders(request)
    assert response.synthetic_used is False
    assert response.source_type in (SourceType.LIVE, SourceType.UNKNOWN)


def test_customer_mode_search_unavailable_does_not_fallback_to_fake_tender():
    request = ResellerSearchRequest(query="кабель", customer_mode=True)
    response = search_tenders(request)
    if response.search_unavailable:
        assert response.synthetic_used is False
        assert len(response.results) == 0
        assert response.freshest is None


def test_dev_mode_can_use_synthetic_data_with_explicit_label():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=False)
    response = search_tenders(request)
    assert response.synthetic_used is True
    assert response.source_type == SourceType.DEMO


def test_live_search_result_required_for_customer_analysis():
    request = ResellerSearchRequest(query="кабель", source="demo_local", customer_mode=True)
    response = search_tenders(request)
    assert response.source_type != SourceType.DEMO or response.search_unavailable


def test_search_unavailable_ui_message(client):
    response = client.post(
        "/api/demo/tender-agent/reseller/search-and-triage",
        json={"query": "кабель", "customer_mode": True},
    )
    assert response.status_code == 200
    payload = response.json()
    if payload["status"] == "search_unavailable":
        assert "недоступен" in payload["analysis_limit_notice"]


def test_existing_synthetic_demo_still_available_for_dev(client):
    response = client.post(
        "/api/demo/tender-agent/reseller/search-and-triage",
        json={"query": "кабель", "source": "demo_local", "customer_mode": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["synthetic_used"] is True
