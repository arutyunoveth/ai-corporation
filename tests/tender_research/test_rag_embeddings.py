from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.shared.db.base import Base
from src.tender_research.config import TenderResearchConfig
from src.tender_research.rag.embeddings import BaseEmbeddingProvider
from src.tender_research.rag.indexer import DocumentEmbeddingIndexer
from src.tender_research.rag.vector_store import JsonVectorStore
from src.tender_research.repository import TenderRepository


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    provider_name = "fake"
    model_name = "fake-model"
    dimension = 3

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vectors.append([
                1.0 if "заявк" in text.lower() else 0.0,
                1.0 if "оплат" in text.lower() else 0.0,
                1.0,
            ])
        return vectors


def _repo(tmp_path):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    repo = TenderRepository(session)
    config = TenderResearchConfig(data_dir=str(tmp_path))
    return repo, config


def test_embeddings_created_and_not_duplicated(tmp_path):
    repo, config = _repo(tmp_path)
    tender = repo.upsert_tender({"source": "eis", "external_id": "t-1", "title": "Tender"})
    document = repo.upsert_document({"tender_id": tender.id, "file_name": "spec.txt"})
    chunk = repo.upsert_document_chunk(
        {
            "tender_id": tender.id,
            "document_id": document.id,
            "chunk_index": 0,
            "text": "Требования к составу заявки.",
            "text_hash": "hash-1",
            "char_start": 0,
            "char_end": 32,
            "token_estimate": 8,
            "source_file_name": "spec.txt",
            "source_text_path": str(tmp_path / "spec.txt"),
        }
    )
    vector_store = JsonVectorStore(Path(tmp_path) / "vectors.json", dimension=3)
    provider = FakeEmbeddingProvider()

    first = DocumentEmbeddingIndexer(repo, config, provider, vector_store).build(limit=10)
    second = DocumentEmbeddingIndexer(repo, config, provider, vector_store).build(limit=10)

    embeddings = repo.list_document_embeddings(
        provider=provider.provider_name,
        model=provider.model_name,
        chunk_ids=[chunk.id],
    )
    assert first["embeddings_created"] == 1
    assert second["embeddings_created"] == 0
    assert second["embeddings_skipped_existing"] == 1
    assert embeddings[0].dimension == 3
    assert embeddings[0].vector_id == chunk.id
