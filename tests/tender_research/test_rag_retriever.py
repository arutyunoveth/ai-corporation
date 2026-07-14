from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.shared.db.base import Base
from src.tender_research.rag.embeddings import BaseEmbeddingProvider
from src.tender_research.rag.retriever import RagRetriever
from src.tender_research.rag.vector_store import JsonVectorStore
from src.tender_research.repository import TenderRepository


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    provider_name = "fake"
    model_name = "fake-model"
    dimension = 2

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append([
                1.0 if "заявк" in lowered else 0.0,
                1.0 if "оплат" in lowered else 0.0,
            ])
        return vectors


def _repo():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    return TenderRepository(session)


def test_retriever_returns_expected_chunks_and_filters(tmp_path):
    repo = _repo()
    t1 = repo.upsert_tender(
        {
            "source": "eis",
            "external_id": "t-1",
            "registry_number": "001",
            "title": "Первая закупка",
            "customer_name": "Заказчик Один",
        }
    )
    d1 = repo.upsert_document({"tender_id": t1.id, "file_name": "a.txt"})
    c1 = repo.upsert_document_chunk(
        {
            "tender_id": t1.id,
            "document_id": d1.id,
            "chunk_index": 0,
            "text": "Требования к составу заявки и участнику.",
            "text_hash": "c1",
            "char_start": 0,
            "char_end": 40,
            "token_estimate": 10,
            "source_file_name": "a.txt",
        }
    )

    t2 = repo.upsert_tender(
        {
            "source": "eis",
            "external_id": "t-2",
            "registry_number": "002",
            "title": "Вторая закупка",
            "customer_name": "Заказчик Два",
        }
    )
    d2 = repo.upsert_document({"tender_id": t2.id, "file_name": "b.txt"})
    c2 = repo.upsert_document_chunk(
        {
            "tender_id": t2.id,
            "document_id": d2.id,
            "chunk_index": 0,
            "text": "Условия оплаты по контракту после приемки.",
            "text_hash": "c2",
            "char_start": 0,
            "char_end": 42,
            "token_estimate": 10,
            "source_file_name": "b.txt",
        }
    )

    provider = FakeEmbeddingProvider()
    store = JsonVectorStore(Path(tmp_path) / "vectors.json", dimension=2)
    store.upsert(c1.id, provider.embed_query(c1.text), {"chunk_id": c1.id})
    store.upsert(c2.id, provider.embed_query(c2.text), {"chunk_id": c2.id})
    store.persist()
    repo.upsert_document_embedding(
        {
            "chunk_id": c1.id,
            "provider": provider.provider_name,
            "model": provider.model_name,
            "dimension": provider.dimension,
            "vector_id": c1.id,
            "embedding_path": str(store.path),
            "embedding_hash": "h1",
        }
    )
    repo.upsert_document_embedding(
        {
            "chunk_id": c2.id,
            "provider": provider.provider_name,
            "model": provider.model_name,
            "dimension": provider.dimension,
            "vector_id": c2.id,
            "embedding_path": str(store.path),
            "embedding_hash": "h2",
        }
    )
    repo._session.commit()

    retriever = RagRetriever(repo, provider, store)
    hits = retriever.search_all_documents("состав заявки", limit=5)
    filtered = retriever.search_documents("условия оплаты", registry_number="002", limit=5)

    assert hits
    assert hits[0].chunk_id == c1.id
    assert filtered
    assert filtered[0].chunk_id == c2.id


def test_retriever_handles_empty_index_gracefully(tmp_path):
    repo = _repo()
    retriever = RagRetriever(repo, FakeEmbeddingProvider(), JsonVectorStore(Path(tmp_path) / "empty.json", dimension=2))

    assert retriever.search_all_documents("что-нибудь", limit=5) == []


def test_retriever_falls_back_to_lexical_search_when_vector_search_is_empty(tmp_path):
    repo = _repo()
    tender = repo.upsert_tender(
        {
            "source": "eis",
            "external_id": "t-lexical",
            "registry_number": "003",
            "title": "Третья закупка",
            "customer_name": "Заказчик Три",
        }
    )
    document = repo.upsert_document({"tender_id": tender.id, "file_name": "contract.txt"})
    chunk = repo.upsert_document_chunk(
        {
            "tender_id": tender.id,
            "document_id": document.id,
            "chunk_index": 0,
            "text": "Порядок оплаты по контракту производится в течение 7 дней после приемки товара.",
            "text_hash": "lexical-1",
            "char_start": 0,
            "char_end": 80,
            "token_estimate": 14,
            "source_file_name": "contract.txt",
        }
    )
    repo._session.commit()

    provider = FakeEmbeddingProvider()
    store = JsonVectorStore(Path(tmp_path) / "vectors-empty.json", dimension=2)
    retriever = RagRetriever(repo, provider, store)

    hits = retriever.search_documents("Каков порядок оплаты по контракту?", registry_number="003", limit=5)

    assert hits
    assert hits[0].chunk_id == chunk.id
    assert hits[0].score > 0
