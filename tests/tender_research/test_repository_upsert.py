from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.shared.db.base import Base
from src.tender_research.repository import TenderRepository


def _db() -> tuple[Session, TenderRepository]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    repo = TenderRepository(s)
    return s, repo


def test_tender_upsert_no_duplicates():
    s, repo = _db()
    data = {
        "source": "eis",
        "external_id": "test-001",
        "title": "Test tender",
        "customer_name": "Test Corp",
        "customer_inn": "1234567890",
        "customer_kpp": "123456789",
        "region": "Moscow",
        "law_type": "44fz",
        "nmck_amount": 1000000.0,
    }
    t1 = repo.upsert_tender(data)
    t2 = repo.upsert_tender(data)
    assert t1.id == t2.id
    assert repo.count_tenders() == 1


def test_customer_upsert():
    s, repo = _db()
    c1 = repo.upsert_customer({"name": "Test Corp", "inn": "1234567890", "kpp": "123456789", "region": "Moscow"})
    c2 = repo.upsert_customer({"name": "Test Corp", "inn": "1234567890", "kpp": "123456789", "region": "SPb"})
    assert c1.id == c2.id
    assert c2.region == "SPb"
    assert c2.tenders_count == 2
    assert repo.count_customers() == 1


def test_web_page_dedupe():
    s, repo = _db()
    tender = repo.upsert_tender({"source": "eis", "external_id": "t-1", "title": "T1"})
    data = {
        "tender_id": tender.id,
        "url": "https://example.com/page",
        "normalized_url": "https://example.com/page",
        "url_hash": "abc123",
        "fetch_status": "fetched",
    }
    p1 = repo.upsert_web_page(data)
    p2 = repo.upsert_web_page(data)
    assert p1.id == p2.id
    assert repo.count_web_pages() == 1
