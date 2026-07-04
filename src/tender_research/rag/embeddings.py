from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from src.tender_research.config import TenderResearchConfig


_TOKEN_RE = re.compile(r"[\w\-]+", re.UNICODE)


class BaseEmbeddingProvider:
    provider_name = "base"
    model_name = "base"
    dimension = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


@dataclass
class HashingEmbeddingProvider(BaseEmbeddingProvider):
    provider_name: str = "hashing"
    model_name: str = "local-hash-v1"
    dimension: int = 256

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = _TOKEN_RE.findall(text.lower())
        for token in tokens:
            token_weight = 1.0 + min(len(token), 24) / 24.0
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign * token_weight
            if len(token) >= 6:
                char_digest = hashlib.sha256(token[:6].encode("utf-8")).digest()
                char_bucket = int.from_bytes(char_digest[:4], "big") % self.dimension
                char_sign = 1.0 if char_digest[4] % 2 == 0 else -1.0
                vector[char_bucket] += char_sign * 0.5
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


@dataclass
class SentenceTransformersEmbeddingProvider(BaseEmbeddingProvider):
    model_name: str

    def __post_init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Install it locally or switch AI_CORP_RAG_EMBEDDINGS_PROVIDER=hashing."
            ) from exc
        self.provider_name = "sentence_transformers"
        self._model = SentenceTransformer(self.model_name)
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]


def build_embedding_provider(config: TenderResearchConfig) -> BaseEmbeddingProvider:
    provider = (config.rag_embeddings_provider or "hashing").strip().lower()
    if provider in {"hash", "hashing", "local_hash"}:
        return HashingEmbeddingProvider(
            provider_name="hashing",
            model_name=config.rag_embeddings_model or "local-hash-v1",
            dimension=int(config.rag_embedding_dimension or 256),
        )
    if provider == "sentence_transformers":
        return SentenceTransformersEmbeddingProvider(
            model_name=config.rag_embeddings_model or "intfloat/multilingual-e5-small",
        )
    raise RuntimeError(f"Unsupported RAG embeddings provider: {config.rag_embeddings_provider}")
