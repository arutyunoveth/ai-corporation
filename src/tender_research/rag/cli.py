from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
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
from src.tender_research.rag.analysis_service import analyze_tender
from src.tender_research.rag.llm import LocalChatLlmClient, SourceCitation, build_source_citations
from src.tender_research.rag.retriever import RagRetriever
from src.tender_research.rag.vector_store import JsonVectorStore
from src.tender_research.repository import TenderRepository

_RUNTIME_ARGS: argparse.Namespace | None = None
_DEFAULT_HASH_PROVIDER_NAMES = {"hash", "hashing", "local_hash"}
_INSUFFICIENT_INFO_MESSAGE = "В найденных документах недостаточно информации для ответа."


@dataclass(frozen=True)
class TenderAnalysisSection:
    title: str
    question: str


@dataclass(frozen=True)
class TenderAnalysisResult:
    title: str
    question: str
    answer: str
    sources: list[SourceCitation]
    llm_error: str | None = None
    used_llm: bool = False


_ANALYZE_TENDER_SECTIONS: tuple[TenderAnalysisSection, ...] = (
    TenderAnalysisSection("1. Требования к заявке", "Требования к содержанию и составу заявки."),
    TenderAnalysisSection("2. Документы участника", "Какие документы должен предоставить участник."),
    TenderAnalysisSection("3. Срок поставки / выполнения", "Срок поставки / выполнения."),
    TenderAnalysisSection("4. Условия оплаты", "Условия оплаты."),
    TenderAnalysisSection("5. Обеспечение заявки / контракта", "Обеспечение заявки / контракта."),
    TenderAnalysisSection("6. Штрафы, пени, ответственность", "Штрафы, пени, ответственность."),
    TenderAnalysisSection("7. Требования к товару / услуге", "Требования к товару / услуге."),
    TenderAnalysisSection("8. Приёмка и закрывающие документы", "Приёмка и закрывающие документы."),
    TenderAnalysisSection("9. Гарантийные обязательства", "Гарантийные обязательства."),
    TenderAnalysisSection("10. Риски и ручная проверка", "Риски участия и что проверить вручную."),
)


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
    if getattr(args, "llm_base_url", None):
        object.__setattr__(config, "local_llm_base_url", args.llm_base_url)
    if getattr(args, "llm_model", None):
        object.__setattr__(config, "local_llm_model", args.llm_model)
    if getattr(args, "llm_timeout_seconds", None):
        object.__setattr__(config, "local_llm_timeout_seconds", args.llm_timeout_seconds)


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


def _add_llm_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--llm-base-url", default=None, help="Local chat LLM base URL override")
    parser.add_argument("--llm-model", default=None, help="Local chat LLM model override")
    parser.add_argument("--llm-timeout-seconds", type=int, default=None, help="Local chat LLM timeout override")


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
    session, _repo, config, provider, _vector_store, retriever = _build_runtime()
    hits = retriever.search_documents(
        args.question,
        registry_number=args.registry_number,
        limit=args.limit,
    )
    llm_enabled = bool(args.use_llm or config.rag_use_llm)
    sources = build_source_citations(hits)

    print(f"registry_number: {args.registry_number}")
    print(f"question: {args.question}")
    print(f"retrieval_provider: {args.provider or provider.provider_name}")
    print(f"retrieval_model: {args.model or provider.model_name}")
    print(f"context_hits: {len(hits)}")
    if llm_enabled:
        print(f"llm_model: {config.local_llm_model}")
        print(f"llm_base_url: {config.local_llm_base_url}")

    if not hits:
        print("answer_mode: retrieval_only")
        print("answer:")
        print("Контекст не найден в локальном индексе.")
        print("sources: 0")
        session.close()
        return

    if llm_enabled:
        answer = _build_local_llm_client(config).generate_answer(
            args.question,
            hits,
            registry_number=args.registry_number,
        )
        if answer.error:
            print("answer_mode: retrieval_fallback")
            print(f"llm_error: {answer.error}")
            print("answer:")
            print("LLM недоступна или не вернула корректный ответ. Ниже релевантные фрагменты.")
            _print_sources(answer.sources or sources)
        else:
            print("answer_mode: local_llm")
            print("answer:")
            print(answer.answer)
            _print_sources(answer.sources)
    else:
        print("answer_mode: retrieval_only")
        print("answer:")
        print("LLM не использовалась. Ниже релевантные фрагменты.")
        _print_sources(sources)
    session.close()


def cmd_analyze_tender(args: argparse.Namespace) -> None:
    session, _repo, config, provider, _vector_store, retriever = _build_runtime()
    llm_enabled = bool(args.use_llm or config.rag_use_llm)
    llm_client = _build_local_llm_client(config) if llm_enabled else None

    results = [
        _analyze_section(
            retriever=retriever,
            registry_number=args.registry_number,
            section=section,
            limit=args.limit,
            llm_client=llm_client,
            use_llm=llm_enabled,
        )
        for section in _ANALYZE_TENDER_SECTIONS
    ]
    markdown = _render_tender_analysis_markdown(
        registry_number=args.registry_number,
        retrieval_provider=args.provider or provider.provider_name,
        retrieval_model=args.model or provider.model_name,
        llm_model=config.local_llm_model if llm_enabled else None,
        results=results,
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        print(f"output_path: {output_path}")
    else:
        print(markdown)
    session.close()


def _analyze_section(
    *,
    retriever: RagRetriever,
    registry_number: str,
    section: TenderAnalysisSection,
    limit: int,
    llm_client: LocalChatLlmClient | None,
    use_llm: bool,
) -> TenderAnalysisResult:
    hits = retriever.search_documents(
        section.question,
        registry_number=registry_number,
        limit=limit,
    )
    sources = build_source_citations(hits)
    llm_hits = hits[:1]
    if not hits:
        return TenderAnalysisResult(
            title=section.title,
            question=section.question,
            answer=_INSUFFICIENT_INFO_MESSAGE,
            sources=[],
        )

    if use_llm and llm_client is not None:
        answer = llm_client.generate_answer(
            section.question,
            llm_hits,
            registry_number=registry_number,
        )
        if answer.error:
            return TenderAnalysisResult(
                title=section.title,
                question=section.question,
                answer=_build_retrieval_only_answer(hits),
                sources=answer.sources or sources,
                llm_error=answer.error,
                used_llm=False,
            )
        return TenderAnalysisResult(
            title=section.title,
            question=section.question,
            answer=answer.answer,
            sources=answer.sources,
            used_llm=True,
        )

    return TenderAnalysisResult(
        title=section.title,
        question=section.question,
        answer=_build_retrieval_only_answer(hits),
        sources=sources,
        used_llm=False,
    )


def _build_retrieval_only_answer(hits) -> str:
    if not hits:
        return _INSUFFICIENT_INFO_MESSAGE
    previews = [f"- {hit.preview}" for hit in hits[:3] if hit.preview]
    if not previews:
        return _INSUFFICIENT_INFO_MESSAGE
    return "LLM не использовалась. Ниже релевантные фрагменты.\n" + "\n".join(previews)
def _build_local_llm_client(config) -> LocalChatLlmClient:
    return LocalChatLlmClient(
        base_url=config.local_llm_base_url,
        model_name=config.local_llm_model,
        timeout_seconds=int(config.local_llm_timeout_seconds or 120),
    )


def _print_sources(sources: list[SourceCitation]) -> None:
    print(f"sources: {len(sources)}")
    for index, source in enumerate(sources, start=1):
        print(f"[source {index}]")
        print(f"registry_number: {source.registry_number}")
        print(f"tender_title: {source.tender_title}")
        print(f"customer: {source.customer_name}")
        print(f"document_file_name: {source.document_file_name}")
        print(f"document_id: {source.document_id}")
        print(f"chunk_id: {source.chunk_id}")
        print(f"score: {source.score:.4f}")
        print(f"preview: {source.quote_preview}")
        print()


def _render_tender_analysis_markdown(
    *,
    registry_number: str,
    retrieval_provider: str,
    retrieval_model: str,
    llm_model: str | None,
    results: list[TenderAnalysisResult],
) -> str:
    lines = [f"# Анализ закупки {registry_number}", ""]
    lines.append(f"Retrieval: `{retrieval_provider}` / `{retrieval_model}`")
    if llm_model:
        lines.append(f"LLM: `{llm_model}`")
    lines.append("")

    unique_sources: dict[tuple[str, str | None], int] = {}
    for result in results:
        lines.append(f"## {result.title}")
        lines.append(result.answer.strip() if result.answer.strip() else _INSUFFICIENT_INFO_MESSAGE)
        lines.append("")
        if result.llm_error:
            lines.append(f"_LLM fallback: {result.llm_error}_")
            lines.append("")
        lines.append("Источники:")
        if result.sources:
            for source in result.sources:
                lines.append(
                    "- "
                    f"{source.document_file_name}, "
                    f"chunk_id={source.chunk_id}, "
                    f"score={source.score:.4f}, "
                    f"registry_number={source.registry_number}"
                )
                source_key = (source.document_file_name, source.registry_number)
                unique_sources[source_key] = unique_sources.get(source_key, 0) + 1
        else:
            lines.append(f"- {_INSUFFICIENT_INFO_MESSAGE}")
        lines.append("")

    lines.append("## Сводка источников")
    if unique_sources:
        for (document_file_name, source_registry_number), chunks_used in sorted(unique_sources.items()):
            lines.append(
                f"- {document_file_name} | chunks used: {chunks_used} | registry_number: {source_registry_number}"
            )
    else:
        lines.append(f"- {_INSUFFICIENT_INFO_MESSAGE}")
    lines.append("")
    return "\n".join(lines)


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
    _add_provider_args(p_ask)
    _add_llm_args(p_ask)

    p_analyze = sub.add_parser("analyze-tender", help="Build a structured RAG analysis report for one registry number")
    p_analyze.add_argument("--registry-number", required=True)
    p_analyze.add_argument("--limit", type=int, default=8)
    p_analyze.add_argument("--use-llm", action="store_true")
    p_analyze.add_argument("--output", default=None, help="Optional markdown output path")
    _add_provider_args(p_analyze)
    _add_llm_args(p_analyze)

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
        elif args.command == "analyze-tender":
            cmd_analyze_tender(args)
    finally:
        _RUNTIME_ARGS = None


if __name__ == "__main__":
    main()
