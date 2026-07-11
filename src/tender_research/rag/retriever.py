from __future__ import annotations

from dataclasses import dataclass

from src.tender_research.rag.embeddings import BaseEmbeddingProvider
from src.tender_research.rag.vector_store import JsonVectorStore
from src.tender_research.repository import TenderRepository


@dataclass(frozen=True)
class RagSearchHit:
    chunk_id: str
    score: float
    registry_number: str | None
    tender_id: str
    tender_title: str
    customer_name: str | None
    document_id: str
    file_name: str
    chunk_index: int
    preview: str
    text: str


class RagRetriever:
    def __init__(
        self,
        repo: TenderRepository,
        provider: BaseEmbeddingProvider,
        vector_store: JsonVectorStore,
    ):
        self._repo = repo
        self._provider = provider
        self._vector_store = vector_store

    def search_documents(
        self,
        query: str,
        *,
        tender_id: str | None = None,
        registry_number: str | None = None,
        customer_name: str | None = None,
        limit: int = 10,
    ) -> list[RagSearchHit]:
        if not query.strip():
            return []

        allowed_chunk_ids = None
        if tender_id or registry_number or customer_name:
            allowed = self._repo.list_chunk_ids_for_filters(
                tender_id=tender_id,
                registry_number=registry_number,
                customer_name=customer_name,
            )
            if not allowed:
                return []
            allowed_chunk_ids = set(allowed)

        query_vector = self._provider.embed_query(query)
        results = self._vector_store.search(
            query_vector,
            limit=limit,
            allowed_vector_ids=allowed_chunk_ids,
        )

        hits: list[RagSearchHit] = []
        for result in results:
            context = self._repo.get_chunk_context(result.vector_id)
            if context is None:
                continue
            preview = context["text"][:280].replace("\n", " ").strip()
            hits.append(
                RagSearchHit(
                    chunk_id=context["chunk_id"],
                    score=result.score,
                    registry_number=context["registry_number"],
                    tender_id=context["tender_id"],
                    tender_title=context["tender_title"],
                    customer_name=context["customer_name"],
                    document_id=context["document_id"],
                    file_name=context["file_name"],
                    chunk_index=context["chunk_index"],
                    preview=preview,
                    text=context["text"],
                )
            )
        return hits
