from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

_load_dotenv_result = load_dotenv(".env", override=False)
_load_dotenv_local_result = load_dotenv(".env.local", override=False)

from src.shared.config.settings import get_settings
from src.shared.db.base import Base
from src.tender_research.config import load_config
from src.tender_research.rag.embeddings import build_embedding_provider
from src.tender_research.rag.indexer import DocumentChunkIndexer, DocumentEmbeddingIndexer
from src.tender_research.rag.retriever import RagRetriever
from src.tender_research.rag.vector_store import JsonVectorStore
from src.tender_research.repository import TenderRepository

_RUNTIME_ARGS: argparse.Namespace | None = None


def _get_session() -> Session:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=engine)()


def _vector_store_path(config) -> str:
    if config.rag_vector_store_path:
        return config.rag_vector_store_path
    return str(Path(config.data_dir) / "rag" / "vector_store.json")


def _build_runtime():
    session = _get_session()
    repo = TenderRepository(session)
    config = load_config()
    if _RUNTIME_ARGS and getattr(_RUNTIME_ARGS, "provider", None):
        object.__setattr__(config, "rag_embeddings_provider", _RUNTIME_ARGS.provider)
    if _RUNTIME_ARGS and getattr(_RUNTIME_ARGS, "model", None):
        object.__setattr__(config, "rag_embeddings_model", _RUNTIME_ARGS.model)
    provider = build_embedding_provider(config)
    vector_store = JsonVectorStore(
        _vector_store_path(config),
        dimension=provider.dimension or None,
    )
    retriever = RagRetriever(repo, provider, vector_store)
    return session, repo, config, provider, vector_store, retriever


def cmd_build_chunks(args: argparse.Namespace) -> None:
    session, repo, config, _provider, _vector_store, _retriever = _build_runtime()
    summary = DocumentChunkIndexer(repo, config).build(limit=args.limit)
    for key in (
        "documents_seen",
        "documents_chunked",
        "chunks_created",
        "chunks_skipped_existing",
        "empty_text_skipped",
    ):
        print(f"{key}: {summary[key]}")
    session.close()


def cmd_build_embeddings(args: argparse.Namespace) -> None:
    session, repo, config, provider, vector_store, _retriever = _build_runtime()
    summary = DocumentEmbeddingIndexer(repo, config, provider, vector_store).build(limit=args.limit)
    for key in (
        "chunks_seen",
        "embeddings_created",
        "embeddings_skipped_existing",
        "model",
        "dimension",
    ):
        print(f"{key}: {summary[key]}")
    session.close()


def cmd_search(args: argparse.Namespace) -> None:
    session, _repo, _config, _provider, _vector_store, retriever = _build_runtime()
    hits = retriever.search_documents(
        args.query,
        tender_id=args.tender_id,
        registry_number=args.registry_number,
        customer_name=args.customer_name,
        limit=args.limit,
    )
    print(f"hits: {len(hits)}")
    for hit in hits:
        print(f"score: {hit.score:.4f}")
        print(f"chunk_id: {hit.chunk_id}")
        print(f"registry_number: {hit.registry_number}")
        print(f"tender_id: {hit.tender_id}")
        print(f"tender_title: {hit.tender_title}")
        print(f"customer: {hit.customer_name}")
        print(f"document: {hit.file_name}")
        print(f"preview: {hit.preview}")
        print()
    session.close()


def cmd_ask(args: argparse.Namespace) -> None:
    session, _repo, config, _provider, _vector_store, retriever = _build_runtime()
    hits = retriever.search_documents(
        args.question,
        registry_number=args.registry_number,
        limit=args.limit,
    )
    print(f"registry_number: {args.registry_number}")
    print(f"question: {args.question}")
    print(f"context_hits: {len(hits)}")
    if not hits:
        print("answer_mode: retrieval_only")
        print("answer: Недостаточно контекста в локальном индексе.")
        session.close()
        return

    if args.use_llm or config.rag_use_llm:
        answer = _ask_local_llm(config, args.question, hits)
        print("answer_mode: local_llm")
        print(f"answer: {answer}")
    else:
        print("answer_mode: retrieval_only")
        for index, hit in enumerate(hits, start=1):
            print(f"[{index}] score={hit.score:.4f} document={hit.file_name} chunk_id={hit.chunk_id}")
            print(hit.text)
            print()
    session.close()


def _ask_local_llm(config, question: str, hits) -> str:
    context = "\n\n".join(
        f"[Источник {index}] {hit.file_name} / {hit.registry_number}\n{hit.text}"
        for index, hit in enumerate(hits, start=1)
    )
    system_prompt = (
        "Отвечай только по предоставленному контексту. "
        "Если контекста недостаточно, так и скажи. "
        "Не придумывай факты и не используй внешние знания."
    )
    payload = {
        "model": config.local_llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"Контекст:\n{context}\n\n"
                    f"Вопрос: {question}\n\n"
                    "Дай короткий ответ строго по контексту."
                ),
            },
        ],
        "temperature": 0,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{config.local_llm_base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = json.loads(response.read().decode("utf-8"))
        return raw["choices"][0]["message"]["content"].strip()
    except urllib.error.URLError as exc:
        return f"Не удалось обратиться к локальной LLM: {exc}"
    except Exception as exc:  # pragma: no cover - safety path
        return f"Ошибка локальной LLM: {exc}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tender Research local RAG CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_chunks = sub.add_parser("build-chunks", help="Build local RAG chunks from extracted texts")
    p_chunks.add_argument("--limit", type=int, default=100)

    p_embeddings = sub.add_parser("build-embeddings", help="Build local embeddings for document chunks")
    p_embeddings.add_argument("--limit", type=int, default=1000)
    p_embeddings.add_argument("--provider", default=None, help="Embedding provider override, e.g. local_hash")
    p_embeddings.add_argument("--model", default=None, help="Embedding model override, e.g. local-hash-v1")

    p_search = sub.add_parser("search", help="Search indexed document chunks")
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--tender-id", default=None)
    p_search.add_argument("--registry-number", default=None)
    p_search.add_argument("--customer-name", default=None)

    p_ask = sub.add_parser("ask", help="Ask a question against one registry number")
    p_ask.add_argument("--registry-number", required=True)
    p_ask.add_argument("--question", required=True)
    p_ask.add_argument("--limit", type=int, default=6)
    p_ask.add_argument("--use-llm", action="store_true")

    return parser


def main() -> None:
    global _RUNTIME_ARGS
    parser = build_parser()
    args = parser.parse_args()
    _RUNTIME_ARGS = args
    try:
        if args.command == "build-chunks":
            cmd_build_chunks(args)
        elif args.command == "build-embeddings":
            cmd_build_embeddings(args)
        elif args.command == "search":
            cmd_search(args)
        elif args.command == "ask":
            cmd_ask(args)
    finally:
        _RUNTIME_ARGS = None


if __name__ == "__main__":
    main()
