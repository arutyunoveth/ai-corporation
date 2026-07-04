from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.shared.db.base import Base
from src.tender_research.repository import TenderRepository


def _postgres_test_url() -> str | None:
    candidates = (
        os.getenv("AI_CORP_POSTGRES_TEST_DATABASE_URL"),
        os.getenv("AI_CORP_ORIGINAL_DATABASE_URL"),
        os.getenv("AI_CORP_DATABASE_URL"),
    )
    for value in candidates:
        if value and value.startswith("postgresql"):
            return value
    return None


@pytest.mark.postgres
def test_postgres_pgvector_extension_and_repository_upserts():
    db_url = _postgres_test_url()
    if not db_url:
        pytest.skip("Postgres integration test requires AI_CORP_POSTGRES_TEST_DATABASE_URL or a postgres AI_CORP_DATABASE_URL")

    engine = create_engine(db_url, future=True)

    with engine.connect() as connection:
        has_vector = connection.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        ).scalar()
    assert has_vector is True

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    repo = TenderRepository(session)

    tender = repo.upsert_tender(
        {
            "source": "eis",
            "external_id": "pg-smoke-001",
            "registry_number": "PG-001",
            "title": "Postgres smoke tender",
            "customer_name": "Arvectum",
            "publication_date": datetime.now(timezone.utc),
            "raw_payload": {"source": "integration-test"},
        }
    )
    tender_again = repo.upsert_tender(
        {
            "source": "eis",
            "external_id": "pg-smoke-001",
            "registry_number": "PG-001",
            "title": "Postgres smoke tender",
            "customer_name": "Arvectum",
            "publication_date": datetime.now(timezone.utc),
            "raw_payload": {"source": "integration-test"},
        }
    )
    assert tender.id == tender_again.id

    document = repo.upsert_document(
        {
            "tender_id": tender.id,
            "file_name": "spec.txt",
            "file_url": "https://example.com/spec.txt",
            "text_extraction_status": "extracted",
            "extracted_text_path": "data/tenders/pg-smoke-001/spec.txt",
            "raw_meta": {"content_type": "text/plain"},
        }
    )
    document_again = repo.upsert_document(
        {
            "tender_id": tender.id,
            "file_name": "spec.txt",
            "file_url": "https://example.com/spec.txt",
            "text_extraction_status": "extracted",
            "extracted_text_path": "data/tenders/pg-smoke-001/spec.txt",
            "raw_meta": {"content_type": "text/plain"},
        }
    )
    assert document.id == document_again.id

    chunk = repo.upsert_document_chunk(
        {
            "tender_id": tender.id,
            "document_id": document.id,
            "chunk_index": 0,
            "text": "Требования к содержанию и составу заявки.",
            "text_hash": "pgvector-chunk-hash-001",
            "char_start": 0,
            "char_end": 40,
            "token_estimate": 8,
            "source_file_name": "spec.txt",
            "source_text_path": "data/tenders/pg-smoke-001/spec.txt",
            "raw_meta": {"source": "integration-test"},
        }
    )
    chunk_again = repo.upsert_document_chunk(
        {
            "tender_id": tender.id,
            "document_id": document.id,
            "chunk_index": 0,
            "text": "Требования к содержанию и составу заявки.",
            "text_hash": "pgvector-chunk-hash-001",
            "char_start": 0,
            "char_end": 40,
            "token_estimate": 8,
            "source_file_name": "spec.txt",
            "source_text_path": "data/tenders/pg-smoke-001/spec.txt",
            "raw_meta": {"source": "integration-test"},
        }
    )
    assert chunk.id == chunk_again.id
    assert len(repo.list_document_chunks(document.id)) == 1

    session.rollback()
    session.close()
