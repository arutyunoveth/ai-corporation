from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from src.shared.config.settings import get_settings
from src.shared.db.diagnostics import get_database_diagnostics, masked_database_url
from src.tender_research.config import load_config
from src.tender_research.rag.analysis_service import analyze_tender
from src.tender_research.rag.schemas import TenderAnalysisResult

router = APIRouter(prefix="/api/tender-research", tags=["tender-research"])


class AnalyzeRequest(BaseModel):
    registry_number: str = Field(..., description="Registry number of the tender")
    provider: str | None = Field(default=None, description="Embedding provider override")
    model: str | None = Field(default=None, description="Embedding model override")
    base_url: str | None = Field(default=None, description="Embedding server base URL override")
    use_llm: bool = Field(default=False, description="Enable local LLM for analysis")
    llm_base_url: str | None = Field(default=None, description="Local LLM base URL override")
    llm_model: str | None = Field(default=None, description="Local LLM model override")
    limit: int = Field(default=6, description="Max chunks per section", ge=1, le=50)
    save_report: bool = Field(default=False, description="Save report markdown to disk")


class SectionSchema(BaseModel):
    id: str
    title: str
    question: str
    answer: str
    sources: list[dict] = []
    status: str = "completed"


class SourceSchema(BaseModel):
    chunk_id: str
    registry_number: str | None
    tender_title: str
    customer_name: str | None
    document_id: str
    document_file_name: str
    score: float
    quote_preview: str


class AnalyzeResponse(BaseModel):
    status: str
    registry_number: str
    sections_count: int
    sources_count: int
    report_markdown: str = ""
    report_path: str | None = None
    used_llm: bool = False
    warnings: list[str] = []
    errors: list[str] = []


class LatestReportResponse(BaseModel):
    registry_number: str
    report_markdown: str
    report_path: str
    created_at: str | None = None


def _to_analyze_response(result: TenderAnalysisResult) -> AnalyzeResponse:
    return AnalyzeResponse(
        status=result.status,
        registry_number=result.registry_number,
        sections_count=result.sections_count,
        sources_count=result.sources_count,
        report_markdown=result.report_markdown,
        report_path=result.report_path,
        used_llm=result.used_llm,
        warnings=result.warnings,
        errors=result.errors,
    )


_TABLE_COUNTS = [
    "procurement_tenders",
    "procurement_tender_documents",
    "procurement_document_chunks",
    "procurement_document_embeddings",
]


class HealthResponse(BaseModel):
    status: str = "ok"
    database_dialect: str | None = None
    database_url_masked: str | None = None
    can_connect: bool = False
    current_migration: str | None = None
    migration_head: str | None = None
    pgvector_extension_available: bool = False
    table_counts: dict[str, int] = {}


@router.get("/health", response_model=HealthResponse)
def tender_research_health() -> HealthResponse:
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    diag = get_database_diagnostics(engine)
    table_counts: dict[str, int] = {}
    if diag.get("can_connect"):
        for table in _TABLE_COUNTS:
            try:
                with engine.connect() as conn:
                    row = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    table_counts[table] = row
            except Exception:
                table_counts[table] = -1
    return HealthResponse(
        status="ok",
        database_dialect=diag.get("database_dialect"),
        database_url_masked=diag.get("database_url_masked"),
        can_connect=diag.get("can_connect", False),
        current_migration=diag.get("current_migration"),
        migration_head=diag.get("migration_head"),
        pgvector_extension_available=diag.get("pgvector_extension_available", False),
        table_counts=table_counts,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_tender_endpoint(payload: AnalyzeRequest) -> AnalyzeResponse:
    try:
        result = analyze_tender(
            registry_number=payload.registry_number,
            provider=payload.provider,
            model=payload.model,
            base_url=payload.base_url,
            use_llm=payload.use_llm,
            llm_base_url=payload.llm_base_url,
            llm_model=payload.llm_model,
            limit=payload.limit,
            save_report=payload.save_report,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return _to_analyze_response(result)


@router.get("/analyze/{registry_number}/latest", response_model=LatestReportResponse)
def get_latest_analysis_report(registry_number: str) -> LatestReportResponse:
    config = load_config()
    reports_dir = Path(config.data_dir) / "rag" / "reports"

    safe_name = _safe_filename(registry_number)
    if safe_name != registry_number:
        raise HTTPException(status_code=400, detail="Invalid registry number")

    report_path = reports_dir / f"analyze_tender_{safe_name}.md"

    resolved = report_path.resolve()
    try:
        resolved.relative_to(reports_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal detected")

    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"No report found for registry_number={registry_number}")

    markdown = report_path.read_text(encoding="utf-8")
    return LatestReportResponse(
        registry_number=registry_number,
        report_markdown=markdown,
        report_path=str(report_path),
    )


def _safe_filename(name: str) -> str:
    import re
    if not name or not re.match(r"^\d{11,25}$", name.strip()):
        return ""
    return name.strip()
