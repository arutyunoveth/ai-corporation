from __future__ import annotations

import json

from sqlalchemy import create_engine

from src.shared.config.settings import get_settings
from src.shared.db.base import Base
from src.tender_research.rag.cli import main


class _FakeResponse:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _setup_db(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "rag-cli.sqlite"
    db_url = f"sqlite:///{db_path}"
    Base.metadata.create_all(create_engine(db_url))
    monkeypatch.setenv("AI_CORP_DATABASE_URL", db_url)
    get_settings.cache_clear()


def test_check_embedding_server_local_hash(tmp_path, monkeypatch, capsys):
    _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr("sys.argv", ["rag", "check-embedding-server", "--provider", "local_hash"])

    main()
    out = capsys.readouterr().out

    assert "provider: local_hash" in out
    assert "reachable: True" in out
    assert "test_embedding_dimension: 256" in out


def test_check_embedding_server_llama_cpp_success(tmp_path, monkeypatch, capsys):
    _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "src.tender_research.rag.embeddings.urllib.request.urlopen",
        lambda request, timeout: _FakeResponse(json.dumps({"data": [{"embedding": [0.1, 0.2, 0.3], "index": 0}]})),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "rag",
            "check-embedding-server",
            "--provider",
            "llama_cpp",
            "--model",
            "Qwen3-Embedding-4B",
            "--base-url",
            "http://127.0.0.1:8090/v1",
        ],
    )

    main()
    out = capsys.readouterr().out

    assert "provider: llama_cpp" in out
    assert "model: Qwen3-Embedding-4B" in out
    assert "base_url: http://127.0.0.1:8090/v1" in out
    assert "reachable: True" in out
    assert "test_embedding_dimension: 3" in out


def test_check_embedding_server_llama_cpp_failure(tmp_path, monkeypatch, capsys):
    from urllib.error import URLError

    _setup_db(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "src.tender_research.rag.embeddings.urllib.request.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(URLError("refused")),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "rag",
            "check-embedding-server",
            "--provider",
            "llama_cpp",
            "--model",
            "Qwen3-Embedding-4B",
        ],
    )

    main()
    out = capsys.readouterr().out

    assert "provider: llama_cpp" in out
    assert "reachable: False" in out
    assert "error: llama.cpp embedding server is not available" in out
