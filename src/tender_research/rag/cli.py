from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

_load_dotenv_result = load_dotenv(".env", override=False)
_load_dotenv_local_result = load_dotenv(".env.local", override=False)

from src.shared.config.settings import get_settings
from src.shared.db.base import Base
from src.tender_research.config import load_config
from src.tender_research.rag.embeddings import build_embedding_provider, probe_embedding_provider
from src.tender_research.rag.indexer import DocumentChunkIndexer, DocumentEmbeddingIndexer
from src.tender_research.rag.retriever import RagRetriever
from src.tender_research.rag.vector_store import JsonVectorStore
from src.tender_research.repository import TenderRepository

_RUNTIME_ARGS: argparse.Namespace | None = None
_DEFAULT_HASH_PROVIDER_NAMES = {"hash", "hashing", "local_hash"}


def _get_session() -> Session:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=engine)()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "default"

def _apply_runtime_overrides(config, args: argparse.Namespace | None) -> None:
    if not args:
        return
    if getattr(args, "provider", None):
        provider = args.provider
        object.__setattr__(config, "rag_embeddings_provider", provider)
        if provider.strip().lower() not in _DEFAULT_HASH_PROVIDER_NAMES:
            object.__setattr__(config, "rag_embedding_dimension", None)
    if getattr(args, "model", None):
        object.__setattr__(config, "rag_embeddings_model", args.model)
    if getattr(args, "base_url", None):
        object.__setattr__(config, "rag_embeddings_base_url", args.base_url)
    if getattr(args, "batch_size", None):
        object.__setattr__(config, "rag_embeddings_batch_size", args.batch_size)
    if getattr(args, "timeout_seconds", None):
        object.__setattr__(config, "rag_embeddings_timeout_seconds", args.timeout_seconds)


def _vector_store_path(config, *, provider_name: str, model_name: str) -> str:
    if config.rag_vector_store_path:
        raw_path = config.rag_vector_store_path.format(
            provider=_slugify(provider_name),
            model=_slugify(model_name),
        )
        path = Path(raw_path)
    else:
        path = Path(config.data_dir) / "rag" / "vector_store.json"

    provider_alias = (config.rag_embeddings_provider or provider_name).strip().lower()
    if provider_alias in _DEFAULT_HASH_PROVIDER_NAMES and model_name == "local-hash-v1":
        return str(path)

    suffix = path.suffix or ".json"
    stem = path.stem if path.suffix else path.name
    named = f"{stem}__{_slugify(provider_name)}__{_slugify(model_name)}{suffix}"
    return str(path.with_name(named))


def _build_runtime():
    session = _get_session()
    repo = TenderRepository(session)
    config = load_config()
    _apply_runtime_overrides(config, _RUNTIME_ARGS)
    provider = build_embedding_provider(config)
    vector_store = JsonVectorStore(
        _vector_store_path(config, provider_name=provider.provider_name, model_name=provider.model_name),
        dimension=provider.dimension or None,
    )
    retriever = RagRetriever(repo, provider, vector_store)
    return session, repo, config, provider, vector_store, retriever


def _add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default=None, help="Embedding provider override, e.g. local_hash or llama_cpp")
    parser.add_argument("--model", default=None, help="Embedding model override")
    parser.add_argument("--base-url", default=None, help="Embedding server base URL override")
    parser.add_argument("--timeout-seconds", type=int, default=None, help="Embedding server timeout override")


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
        "embeddings_failed",
        "provider",
        "model",
        "dimension",
        "batch_size",
        "elapsed_seconds",
        "avg_chunks_per_second",
    ):
        print(f"{key}: {summary[key]}")
    if summary.get("last_error"):
        print(f"last_error: {summary['last_error']}")
    session.close()


def cmd_search(args: argparse.Namespace) -> None:
    session, repo, _config, provider, _vector_store, retriever = _build_runtime()
    embeddings_count = repo.count_document_embeddings(provider=provider.provider_name, model=provider.model_name)
    if embeddings_count == 0:
        print(
            f"No embeddings found for provider={args.provider or provider.provider_name} "
            f"model={args.model or provider.model_name}. Run build-embeddings first."
        )
        session.close()
        return
    hits = retriever.search_documents(
        args.query,
        tender_id=args.tender_id,
        registry_number=args.registry_number,
        customer_name=args.customer_name,
        limit=args.limit,
    )
    print(f"provider: {args.provider or provider.provider_name}")
    print(f"model: {args.model or provider.model_name}")
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


def cmd_check_embedding_server(args: argparse.Namespace) -> None:
    session, _repo, _config, provider, _vector_store, _retriever = _build_runtime()
    info = probe_embedding_provider(provider)
    info["provider"] = args.provider or provider.provider_name
    info["model"] = args.model or provider.model_name
    info["base_url"] = args.base_url or getattr(provider, "base_url", None)
    for key in (
        "provider",
        "base_url",
        "model",
        "reachable",
        "test_embedding_dimension",
        "latency_ms",
    ):
        print(f"{key}: {info.get(key)}")
    if info.get("error"):
        print(f"error: {info['error']}")
    session.close()


def cmd_eval(args: argparse.Namespace) -> None:
    session, repo, config, provider, _vector_store, retriever = _build_runtime()
    questions_path = Path(args.questions)
    questions = json.loads(questions_path.read_text(encoding="utf-8"))

    eval_dir = Path(config.data_dir) / "rag" / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    output_path = eval_dir / (
        f"{_slugify(provider.provider_name)}__{_slugify(provider.model_name)}__"
        f"{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    )

    questions_with_results = 0
    empty_results = 0
    top_scores: list[float] = []
    top_documents: Counter[str] = Counter()

    with output_path.open("w", encoding="utf-8") as handle:
        for item in questions:
            hits = retriever.search_documents(item["query"], limit=args.limit)
            if hits:
                questions_with_results += 1
                top_scores.append(hits[0].score)
                top_documents[hits[0].file_name] += 1
            else:
                empty_results += 1
            row = {
                "id": item["id"],
                "query": item["query"],
                "category": item.get("category"),
                "provider": args.provider or provider.provider_name,
                "model": args.model or provider.model_name,
                "results": [
                    {
                        "score": hit.score,
                        "registry_number": hit.registry_number,
                        "tender_id": hit.tender_id,
                        "tender_title": hit.tender_title,
                        "customer_name": hit.customer_name,
                        "document": hit.file_name,
                        "chunk_id": hit.chunk_id,
                        "preview": hit.preview,
                    }
                    for hit in hits
                ],
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "questions_total": len(questions),
        "questions_with_results": questions_with_results,
        "empty_results": empty_results,
        "avg_top_score": round(sum(top_scores) / len(top_scores), 4) if top_scores else 0.0,
        "top_documents": top_documents.most_common(5),
        "provider": args.provider or provider.provider_name,
        "model": args.model or provider.model_name,
        "output_path": str(output_path),
    }
    for key in (
        "questions_total",
        "questions_with_results",
        "empty_results",
        "avg_top_score",
        "top_documents",
        "provider",
        "model",
        "output_path",
    ):
        print(f"{key}: {summary[key]}")
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
    p_embeddings.add_argument("--batch-size", type=int, default=None, help="Embedding batch size override")
    _add_provider_args(p_embeddings)

    p_search = sub.add_parser("search", help="Search indexed document chunks")
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--tender-id", default=None)
    p_search.add_argument("--registry-number", default=None)
    p_search.add_argument("--customer-name", default=None)
    _add_provider_args(p_search)

    p_ask = sub.add_parser("ask", help="Ask a question against one registry number")
    p_ask.add_argument("--registry-number", required=True)
    p_ask.add_argument("--question", required=True)
    p_ask.add_argument("--limit", type=int, default=6)
    p_ask.add_argument("--use-llm", action="store_true")

    p_check = sub.add_parser("check-embedding-server", help="Check embedding provider reachability and sample dimension")
    _add_provider_args(p_check)

    p_eval = sub.add_parser("eval", help="Run retrieval eval on a set of procurement questions")
    p_eval.add_argument("--questions", required=True, help="Path to evaluation questions JSON")
    p_eval.add_argument("--limit", type=int, default=5, help="Top-k results per question")
    _add_provider_args(p_eval)

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
        elif args.command == "check-embedding-server":
            cmd_check_embedding_server(args)
        elif args.command == "eval":
            cmd_eval(args)
        elif args.command == "search":
            cmd_search(args)
        elif args.command == "ask":
            cmd_ask(args)
    finally:
        _RUNTIME_ARGS = None


if __name__ == "__main__":
    main()
