from src.tender_research.query_builder import build_search_queries


def test_generates_queries():
    queries = build_search_queries(
        tender_title="Поставка компьютерного оборудования для школ",
        customer_name="ГБОУ Школа № 42",
        customer_inn="7712345678",
        max_queries=8,
    )
    assert len(queries) > 0
    assert len(queries) <= 8
    assert all(q.query for q in queries)
    assert all(q.query_type for q in queries)


def test_no_duplicates():
    queries = build_search_queries(
        tender_title="Поставка компьютеров",
        max_queries=20,
    )
    seen = set()
    for q in queries:
        assert q.query not in seen
        seen.add(q.query)


def test_max_queries_limit():
    queries = build_search_queries(
        tender_title="Поставка компьютерного оборудования для государственных нужд Москвы",
        max_queries=3,
    )
    assert len(queries) <= 3


def test_stop_words_removed():
    queries = build_search_queries(
        tender_title="Оказание услуг по уборке помещений для государственных нужд",
        max_queries=5,
    )
    all_text = " ".join(q.query for q in queries).lower()
    assert "государственных" not in all_text
    assert "оказание" not in all_text


def test_short_title_does_not_break():
    queries = build_search_queries(tender_title="Канцелярия", max_queries=5)
    assert len(queries) > 0


def test_registry_number_query():
    queries = build_search_queries(
        tender_title="Тест",
        registry_number="0373100000124000001",
        max_queries=10,
    )
    found = any("0373100000124000001" in q.query for q in queries)
    assert found
