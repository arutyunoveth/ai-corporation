from src.tender_research.providers.manual_urls import ManualUrlsSearchProvider


def test_manual_provider_returns_results():
    provider = ManualUrlsSearchProvider()
    provider.add("Test Supplier", "https://supplier1.ru", "Поставщик оборудования")
    provider.add("Test Corp", "https://corp.ru", "Производитель")
    results = provider.search("test query", limit=5)
    assert len(results) == 2
    assert results[0].title == "Test Supplier"
    assert results[1].url == "https://corp.ru"
    assert results[0].url_hash


def test_manual_provider_limit():
    provider = ManualUrlsSearchProvider()
    for i in range(10):
        provider.add(f"Supplier {i}", f"https://s{i}.ru")
    results = provider.search("test", limit=3)
    assert len(results) == 3
