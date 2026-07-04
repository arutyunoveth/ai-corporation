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


def _make_tender(repo: TenderRepository) -> str:
    t = repo.upsert_tender({"source": "eis", "external_id": "t-1", "title": "Test"})
    return t.id


def test_dedupe_by_source_document_id():
    s, repo = _db()
    tid = _make_tender(repo)
    data = {
        "tender_id": tid,
        "source_document_id": "doc-001",
        "file_name": "spec.pdf",
        "file_url": "https://example.com/spec.pdf",
    }
    d1 = repo.upsert_document(data)
    d2 = repo.upsert_document(data)
    assert d1.id == d2.id
    assert repo.count_documents() == 1


def test_dedupe_by_normalized_file_url():
    s, repo = _db()
    tid = _make_tender(repo)
    data = {
        "tender_id": tid,
        "file_name": "spec.pdf",
        "file_url": "https://example.com/spec.pdf?utm_source=test&other=keep",
    }
    d1 = repo.upsert_document(data)
    d2 = repo.upsert_document({
        "tender_id": tid,
        "file_name": "spec.pdf",
        "file_url": "https://example.com/spec.pdf?other=keep&utm_medium=ignored",
    })
    assert d1.id == d2.id
    assert repo.count_documents() == 1


def test_dedupe_by_file_name_fallback():
    s, repo = _db()
    tid = _make_tender(repo)
    data = {
        "tender_id": tid,
        "file_name": "spec.pdf",
        "size_bytes": 1024,
        "content_type": "application/pdf",
    }
    d1 = repo.upsert_document(data)
    d2 = repo.upsert_document(data)
    assert d1.id == d2.id
    assert repo.count_documents() == 1


def test_sha256_update_does_not_create_second_row():
    s, repo = _db()
    tid = _make_tender(repo)
    data = {
        "tender_id": tid,
        "source_document_id": "doc-001",
        "file_name": "spec.pdf",
    }
    d1 = repo.upsert_document(data)
    assert d1.sha256 is None

    d2 = repo.upsert_document({
        "tender_id": tid,
        "source_document_id": "doc-001",
        "file_name": "spec.pdf",
        "sha256": "abc123",
    })
    assert d1.id == d2.id
    assert d2.sha256 == "abc123"
    assert repo.count_documents() == 1


def test_null_sha256_does_not_duplicate():
    s, repo = _db()
    tid = _make_tender(repo)
    data = {
        "tender_id": tid,
        "source_document_id": "doc-001",
        "file_name": "spec.pdf",
    }
    d1 = repo.upsert_document(data)
    d2 = repo.upsert_document(data)
    assert d1.id == d2.id
    assert repo.count_documents() == 1


def test_url_with_utm_params_gives_same_identity():
    s, repo = _db()
    tid = _make_tender(repo)
    d1 = repo.upsert_document({
        "tender_id": tid,
        "file_name": "spec.pdf",
        "file_url": "https://example.com/doc.pdf?utm_campaign=test&file_id=123",
    })
    d2 = repo.upsert_document({
        "tender_id": tid,
        "file_name": "spec.pdf",
        "file_url": "https://example.com/doc.pdf?file_id=123&utm_source=ignore",
    })
    assert d1.id == d2.id


def test_identity_hash_stored():
    s, repo = _db()
    tid = _make_tender(repo)
    doc = repo.upsert_document({
        "tender_id": tid,
        "source_document_id": "doc-001",
        "file_name": "spec.pdf",
    })
    assert doc.document_identity_hash is not None
    assert doc.document_identity_source == "source_document_id"


def test_identity_source_file_url():
    s, repo = _db()
    tid = _make_tender(repo)
    doc = repo.upsert_document({
        "tender_id": tid,
        "file_name": "spec.pdf",
        "file_url": "https://example.com/doc.pdf",
    })
    assert doc.document_identity_source == "file_url"


def test_identity_source_file_name():
    s, repo = _db()
    tid = _make_tender(repo)
    doc = repo.upsert_document({
        "tender_id": tid,
        "file_name": "spec.pdf",
        "size_bytes": 2048,
        "content_type": "application/pdf",
    })
    assert doc.document_identity_source == "file_name"


def test_different_tender_same_url_is_different_row():
    s, repo = _db()
    t1_id = repo.upsert_tender({"source": "eis", "external_id": "t-1", "title": "T1"}).id
    t2_id = repo.upsert_tender({"source": "eis", "external_id": "t-2", "title": "T2"}).id
    url = "https://example.com/doc.pdf"
    d1 = repo.upsert_document({"tender_id": t1_id, "file_name": "doc.pdf", "file_url": url})
    d2 = repo.upsert_document({"tender_id": t2_id, "file_name": "doc.pdf", "file_url": url})
    assert d1.id != d2.id
    assert repo.count_documents() == 2


def test_backward_compat_finds_by_sha256():
    s, repo = _db()
    tid = _make_tender(repo)
    doc = repo.upsert_document({
        "tender_id": tid,
        "sha256": "abc",
        "file_name": "doc.pdf",
    })
    doc2 = repo.upsert_document({
        "tender_id": tid,
        "sha256": "abc",
        "file_name": "doc.pdf",
        "download_status": "downloaded",
    })
    assert doc.id == doc2.id
    assert doc2.download_status == "downloaded"


def test_second_identity_with_same_sha_merges_without_integrity_error():
    s, repo = _db()
    tid = _make_tender(repo)
    repo.upsert_document({
        "tender_id": tid,
        "source_document_id": "doc-001",
        "file_name": "spec-a.pdf",
    })
    repo.upsert_document({
        "tender_id": tid,
        "source_document_id": "doc-002",
        "file_name": "spec-b.pdf",
    })

    repo.upsert_document({
        "tender_id": tid,
        "source_document_id": "doc-001",
        "file_name": "spec-a.pdf",
        "sha256": "same-sha",
        "download_status": "downloaded",
        "local_path": "data/spec-a.pdf",
    })
    merged = repo.upsert_document({
        "tender_id": tid,
        "source_document_id": "doc-002",
        "file_name": "spec-b.pdf",
        "sha256": "same-sha",
        "download_status": "downloaded",
        "local_path": "data/spec-b.pdf",
    })

    assert repo.count_documents() == 1
    assert merged.sha256 == "same-sha"
    assert merged.download_status == "downloaded"
