"""Trusted R8 canonical-result binding and immutable customer artifact publication."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.modules.customer_pilot.models import PilotArtifact, PilotRunResult, ProcurementCase
from src.tender_research.config import load_config
from src.tender_research.models import TenderAnalysisRun
from src.tender_research.rag.analysis_service import analyze_tender

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_ARTIFACT_TYPE = "final_pdf"
_PDF_RENDERER_VERSION = "r7-persisted-pdf-v2"


def _pdf_artifact_key(registry_number: str, run_id: str, report_model_hash: str) -> str:
    """The frozen R7 identity formula, reproduced without importing demo storage."""
    identity = f"{registry_number}\0{run_id}\0{report_model_hash}\0{_PDF_RENDERER_VERSION}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest()[:24]


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        pass


def _render_pdf(title: str, metadata: list[str], markdown: str, output: Path) -> None:
    """Use the frozen R7 renderer without its demo persistence namespace."""
    from src.modules.tender_operator_agent_demo.report_export_service import _build_pdf_from_parts
    _build_pdf_from_parts(title, metadata, markdown, output)


def _canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _root() -> Path:
    return Path(load_config().data_dir).resolve()


def _relative_path(*segments: str) -> str:
    if any(not _SAFE_SEGMENT.fullmatch(str(segment)) for segment in segments):
        raise RuntimeError("Unsafe server-generated artifact segment")
    return str(Path("customer-pilot").joinpath(*segments))


def _path_under_root(relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise RuntimeError("Unsafe persisted artifact path")
    root = _root()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("Artifact path escapes data root") from exc
    return root / candidate


def _source_graph_hash(result) -> str:
    graph = [
        {"section": section.id, "sources": [source.chunk_id for source in section.sources]}
        for section in result.sections
    ]
    return hashlib.sha256(_canonical_bytes({"source_graph": graph})).hexdigest()


def bind_completed_analysis(session: Session, run: TenderAnalysisRun, case: ProcurementCase) -> PilotRunResult:
    """Run production analysis and atomically persist its server-owned canonical report."""
    existing = session.scalar(select(PilotRunResult).where(PilotRunResult.run_id == run.id))
    if existing:
        return existing
    result = analyze_tender(run.registry_number, session=session, save_report=False, record_history=False)
    if not result.report_markdown:
        raise HTTPException(409, "Analysis did not produce a canonical report")
    canonical = {
        "version": "r8-canonical-report-v1",
        "customer_id": run.customer_id,
        "project_id": run.project_id,
        "procurement_case_id": run.procurement_case_id,
        "run_id": run.id,
        "registry_number": run.registry_number,
        "analysis_status": result.status,
        "report_markdown": result.report_markdown,
        "sections": [
            {
                "id": section.id,
                "title": section.title,
                "question": section.question,
                "answer": section.answer,
                "status": section.status,
                "sources": [
                    {"chunk_id": source.chunk_id, "document_id": source.document_id, "quote_preview": source.quote_preview}
                    for source in section.sources
                ],
            }
            for section in result.sections
        ],
    }
    contents = _canonical_bytes(canonical)
    report_hash = hashlib.sha256(contents).hexdigest()
    source_hash = _source_graph_hash(result)
    relative = f"{_relative_path(str(run.customer_id), str(run.project_id), str(case.id), str(run.id))}/canonical-report.json"
    target = _path_under_root(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and (target.is_symlink() or not target.is_file()):
        raise HTTPException(409, "Canonical report storage is unsafe")
    if not target.exists():
        descriptor, name = tempfile.mkstemp(prefix=".canonical-", suffix=".partial", dir=target.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(contents); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, target)
            _fsync_directory(target.parent)
        finally:
            temporary.unlink(missing_ok=True)
    elif target.read_bytes() != contents:
        raise HTTPException(409, "Canonical report storage conflicts with this run")
    binding = PilotRunResult(
        customer_id=run.customer_id, project_id=run.project_id, procurement_case_id=case.id,
        run_id=run.id, source_analysis_run_id=result.run_id,
        canonical_report_storage_key=relative, canonical_report_hash=report_hash,
        source_graph_hash=source_hash, production_model_hash=report_hash,
    )
    session.add(binding)
    session.flush()
    return binding


def _load_canonical(run: TenderAnalysisRun, case: ProcurementCase, binding: PilotRunResult) -> dict:
    if (binding.customer_id, binding.project_id, binding.procurement_case_id, binding.run_id) != (run.customer_id, run.project_id, case.id, run.id):
        raise HTTPException(409, "Canonical result ownership is invalid")
    path = _path_under_root(binding.canonical_report_storage_key)
    if path.is_symlink() or not path.is_file():
        raise HTTPException(409, "Canonical report is missing or unsafe")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(422, "Canonical report is invalid") from exc
    encoded = _canonical_bytes(data)
    if hashlib.sha256(encoded).hexdigest() != binding.canonical_report_hash:
        raise HTTPException(409, "Canonical report hash is invalid")
    expected = {"customer_id": run.customer_id, "project_id": run.project_id, "procurement_case_id": case.id, "run_id": run.id, "registry_number": run.registry_number}
    if any(data.get(key) != value for key, value in expected.items()):
        raise HTTPException(409, "Canonical report ownership is invalid")
    if not isinstance(data.get("report_markdown"), str) or not data["report_markdown"].strip():
        raise HTTPException(422, "Canonical report has no renderable content")
    return data


def publish_final_pdf(session: Session, run: TenderAnalysisRun, case: ProcurementCase) -> PilotArtifact:
    existing = session.scalar(select(PilotArtifact).where(PilotArtifact.run_id == run.id, PilotArtifact.artifact_type == _ARTIFACT_TYPE))
    if existing:
        binding = session.scalar(select(PilotRunResult).where(PilotRunResult.id == existing.run_result_id))
        if not binding:
            raise HTTPException(409, "Final artifact binding is missing")
        from src.modules.customer_pilot.artifacts import verified_pilot_artifact
        verified_pilot_artifact(run, case, binding, existing)
        return existing
    if run.status != "completed" or case.status != "operator_review":
        raise HTTPException(409, "Final PDF can be published only after canonical completion")
    binding = session.scalar(select(PilotRunResult).where(PilotRunResult.run_id == run.id))
    if not binding:
        raise HTTPException(409, "Canonical result is required before publication")
    canonical = _load_canonical(run, case, binding)
    artifact_key = _pdf_artifact_key(run.registry_number, run.id, binding.canonical_report_hash)
    directory_rel = _relative_path(str(run.customer_id), str(run.project_id), str(case.id), str(run.id))
    pdf_rel = f"{directory_rel}/{artifact_key}.pdf"
    manifest_rel = f"{directory_rel}/{artifact_key}.manifest.json"
    pdf_path, manifest_path = _path_under_root(pdf_rel), _path_under_root(manifest_rel)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = pdf_path.with_suffix(".pdf.lock")
    with lock_path.open("a+b") as lock:
        try:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        except ImportError:  # pragma: no cover
            pass
        for partial in (pdf_path.with_suffix(".pdf.partial"), manifest_path.with_suffix(".json.partial")):
            partial.unlink(missing_ok=True)
        if not (pdf_path.exists() and manifest_path.exists()):
            if pdf_path.exists() or manifest_path.exists():
                pdf_path.unlink(missing_ok=True); manifest_path.unlink(missing_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=".pdf-", suffix=".partial", dir=pdf_path.parent)
            temporary = Path(name)
            try:
                os.close(descriptor)
                _render_pdf(f"Анализ закупки {run.registry_number}", [f"Реестровый номер: {run.registry_number}", f"Run: {run.id}"], canonical["report_markdown"], temporary)
                bytes_ = temporary.read_bytes()
                if not bytes_.startswith(b"%PDF-") or not bytes_:
                    raise RuntimeError("Generated PDF is invalid")
                with temporary.open("rb") as handle: os.fsync(handle.fileno())
                os.replace(temporary, pdf_path)
                digest = hashlib.sha256(bytes_).hexdigest()
                manifest = {
                    "customer_id": run.customer_id, "project_id": run.project_id, "procurement_case_id": case.id, "run_id": run.id,
                    "run_result_id": binding.id, "registry_number": run.registry_number, "run_namespace_key": run.artifact_key,
                    "artifact_key": artifact_key, "artifact_type": _ARTIFACT_TYPE, "report_model_hash": binding.canonical_report_hash,
                    "source_graph_hash": binding.source_graph_hash, "renderer_version": _PDF_RENDERER_VERSION,
                    "pdf_relative_path": pdf_rel, "pdf_sha256": digest, "byte_size": len(bytes_), "created_at": binding.completed_at.isoformat(),
                }
                partial = manifest_path.with_suffix(".json.partial")
                with partial.open("wb") as handle:
                    handle.write(_canonical_bytes(manifest)); handle.flush(); os.fsync(handle.fileno())
                os.replace(partial, manifest_path); _fsync_directory(pdf_path.parent)
            finally:
                temporary.unlink(missing_ok=True)
    from src.modules.customer_pilot.artifacts import verified_pilot_artifact
    payload = verified_pilot_artifact(run, case, binding, None, manifest_path=manifest_rel)
    artifact = PilotArtifact(
        customer_id=run.customer_id, project_id=run.project_id, procurement_case_id=case.id, run_id=run.id, run_result_id=binding.id,
        artifact_type=_ARTIFACT_TYPE, artifact_key=artifact_key, report_model_hash=binding.canonical_report_hash,
        source_graph_hash=binding.source_graph_hash, renderer_version=_PDF_RENDERER_VERSION, manifest_relative_path=manifest_rel,
        pdf_relative_path=pdf_rel, pdf_sha256=payload["pdf_sha256"], byte_size=payload["byte_size"], status="published",
    )
    session.add(artifact)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        winner = session.scalar(select(PilotArtifact).where(PilotArtifact.run_id == run.id, PilotArtifact.artifact_type == _ARTIFACT_TYPE))
        if winner:
            winner_binding = session.scalar(select(PilotRunResult).where(PilotRunResult.id == winner.run_result_id))
            if not winner_binding:
                raise HTTPException(409, "Concurrent final artifact binding is missing")
            verified_pilot_artifact(run, case, winner_binding, winner)
            return winner
        raise
    return artifact
