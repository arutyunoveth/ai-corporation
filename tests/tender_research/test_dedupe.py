from src.tender_research.dedupe import is_private_url, normalize_url, url_hash


def test_normalize_url_removes_tracking():
    url = "https://example.com/page?utm_source=twitter&foo=bar"
    norm = normalize_url(url)
    assert "utm_source" not in norm
    assert "foo=bar" in norm


def test_normalize_url_removes_www():
    url = "https://www.example.com/path/"
    norm = normalize_url(url)
    assert "www." not in norm
    assert norm.endswith("/path")


def test_normalize_url_trailing_slash():
    assert normalize_url("https://example.com").endswith("/")
    assert normalize_url("https://example.com/") == normalize_url("https://example.com")


def test_url_hash_deterministic():
    h1 = url_hash("https://example.com/page")
    h2 = url_hash("https://example.com/page")
    assert h1 == h2


def test_private_url_localhost():
    assert is_private_url("http://localhost:8080/test")
    assert is_private_url("http://127.0.0.1/test")
    assert is_private_url("http://10.0.0.1/test")
    assert is_private_url("http://192.168.1.1/test")
    assert is_private_url("file:///etc/passwd")
    assert is_private_url("http://172.16.0.1/test")


def test_public_url_not_private():
    assert not is_private_url("https://example.com/test")
    assert not is_private_url("https://yandex.ru/search")
    assert not is_private_url("https://zakupki.gov.ru")
