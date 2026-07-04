from __future__ import annotations

import io
import json
from urllib.error import HTTPError, URLError

import pytest

from src.tender_research.rag.embeddings import (
    EmbeddingProviderError,
    EmbeddingServerUnavailableError,
    LlamaCppEmbeddingProvider,
)


class _FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_llama_cpp_embeddings_success_batch_and_auto_dimension(monkeypatch):
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(
            json.dumps(
                {
                    "data": [
                        {"embedding": [0.1, 0.2, 0.3], "index": 0},
                        {"embedding": [0.4, 0.5, 0.6], "index": 1},
                    ]
                }
            )
        )

    monkeypatch.setattr("src.tender_research.rag.embeddings.urllib.request.urlopen", fake_urlopen)
    provider = LlamaCppEmbeddingProvider(
        model_name="Qwen3-Embedding-4B",
        base_url="http://127.0.0.1:8090/v1",
        timeout_seconds=42,
    )

    vectors = provider.embed_texts(["alpha", "beta"])

    assert captured["url"] == "http://127.0.0.1:8090/v1/embeddings"
    assert captured["timeout"] == 42
    assert captured["payload"] == {"model": "Qwen3-Embedding-4B", "input": ["alpha", "beta"]}
    assert vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert provider.dimension == 3


def test_llama_cpp_embeddings_server_unavailable(monkeypatch):
    monkeypatch.setattr(
        "src.tender_research.rag.embeddings.urllib.request.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(URLError("refused")),
    )
    provider = LlamaCppEmbeddingProvider("Qwen3-Embedding-4B", "http://127.0.0.1:8090/v1")

    with pytest.raises(EmbeddingServerUnavailableError, match="llama.cpp embedding server is not available"):
        provider.embed_texts(["alpha"])


def test_llama_cpp_embeddings_non_json_response(monkeypatch):
    monkeypatch.setattr(
        "src.tender_research.rag.embeddings.urllib.request.urlopen",
        lambda request, timeout: _FakeResponse("not-json"),
    )
    provider = LlamaCppEmbeddingProvider("Qwen3-Embedding-4B", "http://127.0.0.1:8090/v1")

    with pytest.raises(EmbeddingProviderError, match="non-JSON response"):
        provider.embed_texts(["alpha"])


def test_llama_cpp_embeddings_dimension_mismatch(monkeypatch):
    monkeypatch.setattr(
        "src.tender_research.rag.embeddings.urllib.request.urlopen",
        lambda request, timeout: _FakeResponse(
            json.dumps(
                {
                    "data": [
                        {"embedding": [0.1, 0.2], "index": 0},
                        {"embedding": [0.3, 0.4, 0.5], "index": 1},
                    ]
                }
            )
        ),
    )
    provider = LlamaCppEmbeddingProvider("Qwen3-Embedding-4B", "http://127.0.0.1:8090/v1")

    with pytest.raises(EmbeddingProviderError, match="inconsistent dimensions"):
        provider.embed_texts(["alpha", "beta"])


def test_llama_cpp_embeddings_404_endpoint(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 404, "not found", hdrs=None, fp=io.BytesIO(b"missing"))

    monkeypatch.setattr("src.tender_research.rag.embeddings.urllib.request.urlopen", fake_urlopen)
    provider = LlamaCppEmbeddingProvider("Qwen3-Embedding-4B", "http://127.0.0.1:8090/v1")

    with pytest.raises(EmbeddingProviderError, match="llama.cpp embedding server is not available"):
        provider.embed_texts(["alpha"])
