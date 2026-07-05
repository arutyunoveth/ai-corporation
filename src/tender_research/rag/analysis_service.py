from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.shared.config.settings import get_settings
from src.shared.db.base import Base
from src.tender_research.config import load_config
from src.tender_research.rag.embeddings import build_embedding_provider
from src.tender_research.rag.history_service import record_analysis_run
from src.tender_research.rag.llm import (
    LocalChatLlmClient,
    build_source_citations,
)
from src.tender_research.rag.retriever import RagRetriever, RagSearchHit
from src.tender_research.rag.schemas import (
    ANALYSIS_SECTIONS,
    SourceCitation,
    TenderAnalysisResult,
    TenderAnalysisSection,
)
from src.tender_research.rag.vector_store import JsonVectorStore
from src.tender_research.repository import TenderRepository

logger = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    import re
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "default"


_DEFAULT_HASH_PROVIDER_NAMES = {"hash", "hashing", "local_hash"}


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


def _get_session() -> Session:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker
    return sessionmaker(bind=engine)()


def _build_report_markdown(
    registry_number: str,
    sections: list[TenderAnalysisSection],
    used_llm: bool,
    llm_model: str | None,
    retrieval_provider: str | None,
    retrieval_model: str | None,
) -> str:
    lines = [
        f"# Анализ закупки {registry_number}",
        "",
        f"**Статус:** завершено",
        f"**LLM:** {'да' if used_llm else 'нет'} {f'({llm_model})' if llm_model and used_llm else ''}",
        f"**Поиск:** {retrieval_provider or '?'} / {retrieval_model or '?'}",
        f"**Разделов:** {len(sections)}",
        f"**Источников:** {sum(len(s.sources) for s in sections)}",
        "",
        "---",
        "",
    ]
    for section in sections:
        lines.append(f"## {section.id}. {section.title}")
        lines.append("")
        if section.status == "insufficient_context":
            lines.append("*Недостаточно контекста в документах для ответа.*")
            lines.append("")
            continue
        if section.status == "no_context":
            lines.append("*Нет документов для анализа.*")
            lines.append("")
            continue
        lines.append(section.answer)
        lines.append("")
        if section.sources:
            lines.append("**Источники:**")
            lines.append("")
            for idx, src in enumerate(section.sources, start=1):
                lines.append(f"{idx}. **{src.document_file_name}**")
                lines.append(f"   - chunk_id: `{src.chunk_id}`")
                lines.append(f"   - registry_number: {src.registry_number or '-'}")
                lines.append(f"   - tender_title: {src.tender_title}")
                lines.append(f"   - score: {src.score:.4f}")
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def _save_report(report_markdown: str, registry_number: str, data_dir: str) -> str:
    reports_dir = Path(data_dir) / "rag" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = reports_dir / f"analyze_tender_{registry_number}.md"
    output_path.write_text(report_markdown, encoding="utf-8")
    return str(output_path)


def _record_history(
    result: TenderAnalysisResult,
    session: Session,
    *,
    duration_seconds: float | None = None,
    source: str | None = None,
) -> str | None:
    try:
        run = record_analysis_run(
            session,
            registry_number=result.registry_number,
            status=result.status,
            used_llm=result.used_llm,
            llm_model=result.llm_model,
            retrieval_provider=result.retrieval_provider,
            retrieval_model=result.retrieval_model,
            sections_count=result.sections_count,
            sources_count=result.sources_count,
            report_path=result.report_path,
            report_markdown=result.report_markdown,
            warnings=result.warnings,
            errors=result.errors,
            duration_seconds=duration_seconds,
            source=source,
        )
        return run.id
    except Exception as e:
        logger.warning("Analysis completed, but history record was not saved: %s", e)
        return None


def analyze_tender(
    registry_number: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    timeout_seconds: int | None = None,
    batch_size: int | None = None,
    use_llm: bool = False,
    llm_base_url: str | None = None,
    llm_model: str | None = None,
    llm_timeout_seconds: int | None = None,
    limit: int = 6,
    session: Session | None = None,
    save_report: bool = False,
    record_history: bool = True,
    history_source: str | None = None,
) -> TenderAnalysisResult:
    own_session = False
    if session is None:
        session = _get_session()
        own_session = True

    try:
        warnings: list[str] = []
        errors: list[str] = []
        config = load_config()
        _start_time: float | None = None
        if record_history:
            import time
            _start_time = time.time()

        if provider:
            object.__setattr__(config, "rag_embeddings_provider", provider)
            if provider.strip().lower() not in _DEFAULT_HASH_PROVIDER_NAMES:
                object.__setattr__(config, "rag_embedding_dimension", None)
        if model:
            object.__setattr__(config, "rag_embeddings_model", model)
        if base_url:
            object.__setattr__(config, "rag_embeddings_base_url", base_url)
        if timeout_seconds:
            object.__setattr__(config, "rag_embeddings_timeout_seconds", timeout_seconds)
        if batch_size:
            object.__setattr__(config, "rag_embeddings_batch_size", batch_size)
        if llm_base_url:
            object.__setattr__(config, "local_llm_base_url", llm_base_url)
        if llm_model:
            object.__setattr__(config, "local_llm_model", llm_model)
        if llm_timeout_seconds:
            object.__setattr__(config, "local_llm_timeout_seconds", llm_timeout_seconds)

        repo = TenderRepository(session)
        tender = repo.get_tender_by_registry_number(registry_number)
        if not tender:
            tender = repo.get_tender_by_external("eis", registry_number)
        if not tender:
            tender = repo.get_tender_by_external("external_public_44fz", registry_number)
        if not tender:
            result = TenderAnalysisResult(
                status="no_context",
                registry_number=registry_number,
                sections=[],
                sections_count=0,
                sources_count=0,
                errors=[f"Tender {registry_number} not found in database"],
            )
            if record_history:
                _record_history(result, session, duration_seconds=None, source=history_source)
            return result

        emb_provider = build_embedding_provider(config)
        vector_store = JsonVectorStore(
            _vector_store_path(config, provider_name=emb_provider.provider_name, model_name=emb_provider.model_name),
            dimension=emb_provider.dimension or None,
        )
        retriever = RagRetriever(repo, emb_provider, vector_store)

        embeddings_count = repo.count_document_embeddings(
            provider=emb_provider.provider_name,
            model=emb_provider.model_name,
        )
        if embeddings_count == 0:
            result = TenderAnalysisResult(
                status="no_context",
                registry_number=registry_number,
                sections=[],
                sections_count=0,
                sources_count=0,
                errors=[f"No embeddings found for provider={emb_provider.provider_name} model={emb_provider.model_name}. Run build-embeddings first."],
                retrieval_provider=emb_provider.provider_name,
                retrieval_model=emb_provider.model_name,
            )
            if record_history:
                _record_history(result, session, duration_seconds=None, source=history_source)
            return result

        llm_client: LocalChatLlmClient | None = None
        if use_llm:
            try:
                llm_client = LocalChatLlmClient(
                    base_url=config.local_llm_base_url,
                    model_name=config.local_llm_model,
                    timeout_seconds=int(config.local_llm_timeout_seconds or 120),
                )
            except Exception as e:
                warnings.append(f"LLM client init failed: {e}")
                use_llm = False

        sections: list[TenderAnalysisSection] = []
        all_sources: list[SourceCitation] = []

        for sec_def in ANALYSIS_SECTIONS:
            hits = retriever.search_documents(
                sec_def["question"],
                registry_number=registry_number,
                limit=limit,
            )
            sources = build_source_citations(hits)
            all_sources.extend(sources)

            if not hits:
                sections.append(TenderAnalysisSection(
                    id=sec_def["id"],
                    title=sec_def["title"],
                    question=sec_def["question"],
                    answer="",
                    sources=[],
                    status="insufficient_context" if llm_client else "no_context",
                ))
                continue

            if use_llm and llm_client:
                answer = llm_client.generate_answer(
                    sec_def["question"],
                    hits,
                    registry_number=registry_number,
                )
                if answer.error:
                    answer_text = _retrieval_only_answer(hits)
                    status = "completed_with_warning" if answer.sources else "retrieval_only"
                    if not warnings or not any("LLM" in w for w in warnings):
                        warnings.append(f"LLM unavailable for section {sec_def['id']}: {answer.error}")
                else:
                    answer_text = answer.answer
                    status = "completed"
            else:
                answer_text = _retrieval_only_answer(hits)
                status = "retrieval_only"

            sections.append(TenderAnalysisSection(
                id=sec_def["id"],
                title=sec_def["title"],
                question=sec_def["question"],
                answer=answer_text,
                sources=sources,
                status=status,
            ))

        overall_status = "completed"
        if errors:
            overall_status = "failed"
        elif any(s.status in ("insufficient_context", "no_context") for s in sections):
            if use_llm:
                overall_status = "completed_with_warnings"
            else:
                overall_status = "completed_with_warnings"

        report_markdown = _build_report_markdown(
            registry_number=registry_number,
            sections=sections,
            used_llm=use_llm and llm_client is not None,
            llm_model=config.local_llm_model if use_llm else None,
            retrieval_provider=emb_provider.provider_name,
            retrieval_model=emb_provider.model_name,
        )

        report_path = None
        if save_report:
            report_path = _save_report(report_markdown, registry_number, config.data_dir)

        result = TenderAnalysisResult(
            status=overall_status,
            registry_number=registry_number,
            sections=sections,
            sections_count=len(sections),
            sources_count=len(set(s.chunk_id for s in all_sources)),
            report_markdown=report_markdown,
            report_path=report_path,
            used_llm=use_llm and llm_client is not None,
            llm_model=config.local_llm_model if use_llm else None,
            retrieval_provider=emb_provider.provider_name,
            retrieval_model=emb_provider.model_name,
            warnings=warnings,
            errors=errors,
        )
        if record_history:
            duration = None
            if _start_time is not None:
                import time
                duration = time.time() - _start_time
            _record_history(result, session, duration_seconds=duration, source=history_source)
        return result
    finally:
        if own_session:
            session.close()


def _retrieval_only_answer(hits: list[RagSearchHit]) -> str:
    lines = ["Релевантные фрагменты из документов:", ""]
    for idx, hit in enumerate(hits[:6], start=1):
        lines.append(f"[Фрагмент {idx}]")
        lines.append(f"  Документ: {hit.file_name}")
        lines.append(f"  Раздел: {hit.chunk_index}")
        lines.append(f"  Релевантность: {hit.score:.4f}")
        lines.append("  Текст:")
        for text_line in hit.text.strip().split("\n")[:10]:
            lines.append(f"    {text_line}")
        lines.append("")
    return "\n".join(lines)
