"""Trusted R8 binding and PDF publication from immutable canonical snapshots."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.modules.customer_pilot.canonical_snapshot import (
    CanonicalSnapshotConflictError,
    CanonicalSnapshotError,
    publish_canonical_snapshot,
)
from src.modules.customer_pilot.input_resolver import resolve_customer_run_inputs
from src.modules.customer_pilot.binding_verifier import (
    RunSnapshotBindingError,
    verify_run_snapshot_binding,
)
from src.modules.customer_pilot.artifact_snapshot import (
    FinalPdfArtifactConflictError,
    FinalPdfArtifactError,
    derive_final_pdf_artifact_identity,
    publish_final_pdf_generation,
)
from src.modules.customer_pilot.models import (
    PilotArtifact,
    PilotRunResult,
    ProcurementCase,
)
from src.modules.procurement_analysis.frozen_producer import (
    produce_frozen_canonical_analysis,
)
from src.tender_research.config import load_config
from src.tender_research.models import TenderAnalysisRun

_ARTIFACT_TYPE = "final_pdf"
_PDF_RENDERER_VERSION = "r7-persisted-pdf-v2"


def _root() -> Path:
    return Path(load_config().data_dir)


def _path_under_root(relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise HTTPException(409, "Persisted artifact path is unsafe")
    return _root() / candidate


def _source_analysis_run_id(run: TenderAnalysisRun) -> str:
    return str(uuid5(NAMESPACE_URL, f"arvectum:frozen-r7-source:{run.id}"))


def _customer_metadata(run: TenderAnalysisRun, case: ProcurementCase) -> dict:
    """Server-owned metadata only; callers cannot inject report fields or hashes."""
    return {
        "run_id": run.id,
        "procurement_id": run.registry_number,
        "tender_title": f"Закупка {run.registry_number}",
        "tender_category": "Закупка",
        "customer_name": str(run.customer_id),
        "status": "completed",
        "warnings": [],
        "limitations": [
            "Документы для закупки требуют операторской проверки в pilot-контуре."
        ],
        "files": [],
        "procurement": {"registry_number": run.registry_number, "case_id": case.id},
    }


def _verified_binding(
    run: TenderAnalysisRun, case: ProcurementCase, binding: PilotRunResult
) -> object:
    if not binding.is_verified_snapshot_binding:
        raise HTTPException(409, "Canonical snapshot binding is incomplete")
    if (
        binding.customer_id,
        binding.project_id,
        binding.procurement_case_id,
        binding.run_id,
    ) != (run.customer_id, run.project_id, case.id, run.id):
        raise HTTPException(409, "Canonical snapshot ownership is invalid")
    try:
        return verify_run_snapshot_binding(run=run, case=case, binding=binding)
    except RunSnapshotBindingError as exc:
        raise HTTPException(409, "Canonical snapshot identities are invalid") from exc


def bind_completed_analysis(
    session: Session, run: TenderAnalysisRun, case: ProcurementCase
) -> PilotRunResult:
    """Produce frozen R7 bytes, snapshot them, then bind all identities to DB."""
    existing = session.scalar(
        select(PilotRunResult).where(PilotRunResult.run_id == run.id)
    )
    if existing and existing.is_verified_snapshot_binding:
        _verified_binding(run, case, existing)
        return existing
    source_run_id = _source_analysis_run_id(run)
    try:
        inputs = resolve_customer_run_inputs(session, run.registry_number)
        with tempfile.TemporaryDirectory(prefix="r8-frozen-producer-") as directory:
            production = produce_frozen_canonical_analysis(
                registry_number=run.registry_number,
                run_id=run.id,
                output_dir=Path(directory),
                metadata={
                    **_customer_metadata(run, case),
                    "warnings": inputs.warnings,
                    "limitations": inputs.limitations,
                },
                documents=inputs.documents,
                source_analysis_run_id=source_run_id,
            )
            snapshot = publish_canonical_snapshot(
                customer_id=run.customer_id,
                project_id=run.project_id,
                procurement_case_id=case.id,
                run_id=run.id,
                registry_number=run.registry_number,
                source_analysis_run_id=production.source_analysis_run_id,
                verified=production.persisted,
            )
    except CanonicalSnapshotConflictError as exc:
        raise HTTPException(
            409, "Immutable canonical snapshot conflicts with this run"
        ) from exc
    except CanonicalSnapshotError as exc:
        raise HTTPException(
            422, "Frozen canonical snapshot cannot be published"
        ) from exc
    except Exception as exc:
        # The R7 producer is fail-closed; no synthetic report fallback exists.
        raise HTTPException(
            422, "Frozen R7 analysis did not produce a trusted result"
        ) from exc
    values = {
        "customer_id": run.customer_id,
        "project_id": run.project_id,
        "procurement_case_id": case.id,
        "run_id": run.id,
        "source_analysis_run_id": production.source_analysis_run_id,
        "canonical_report_storage_key": snapshot.canonical_report_relative_path,
        "canonical_report_hash": None,
        "source_graph_hash": snapshot.source_graph_hash,
        "production_model_hash": snapshot.production_model_hash,
        "requirements_storage_key": snapshot.requirements_relative_path,
        "requirements_file_sha256": snapshot.requirements_file_sha256,
        "canonical_report_file_sha256": snapshot.canonical_report_file_sha256,
        "binding_manifest_storage_key": snapshot.binding_manifest_relative_path,
        "binding_manifest_file_sha256": snapshot.binding_manifest_file_sha256,
        "source_graph_hash_algorithm": snapshot.source_graph_hash_algorithm,
        "report_model_hash": snapshot.report_model_hash,
        "verification_policy_version": snapshot.verification_policy_version,
    }
    if existing:
        for name, value in values.items():
            setattr(existing, name, value)
        binding = existing
    else:
        binding = PilotRunResult(**values)
        session.add(binding)
    session.flush()
    if not binding.is_verified_snapshot_binding:
        raise HTTPException(409, "Canonical snapshot binding is incomplete")
    return binding


def _load_canonical(
    run: TenderAnalysisRun, case: ProcurementCase, binding: PilotRunResult
) -> dict:
    try:
        verified = _verified_binding(run, case, binding)
        return json.loads(verified.canonical_report_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "Canonical snapshot report is invalid") from exc


def publish_final_pdf(
    session: Session, run: TenderAnalysisRun, case: ProcurementCase
) -> tuple[PilotArtifact, bool]:
    existing = session.scalar(
        select(PilotArtifact).where(
            PilotArtifact.run_id == run.id,
            PilotArtifact.artifact_type == _ARTIFACT_TYPE,
        )
    )
    if existing:
        binding = session.scalar(
            select(PilotRunResult).where(PilotRunResult.id == existing.run_result_id)
        )
        if not binding:
            raise HTTPException(409, "Final artifact binding is missing")
        from src.modules.customer_pilot.artifacts import verified_pilot_artifact

        verified_pilot_artifact(run, case, binding, existing)
        return existing, False
    if run.status != "completed" or case.status not in {
        "operator_review",
        "client_ready",
        "delivered",
    }:
        raise HTTPException(
            409, "Final PDF can be published only after canonical completion"
        )
    binding = session.scalar(
        select(PilotRunResult).where(PilotRunResult.run_id == run.id)
    )
    if not binding:
        raise HTTPException(409, "Canonical result is required before publication")
    canonical = _load_canonical(run, case, binding)
    identity = derive_final_pdf_artifact_identity(
        registry_number=run.registry_number,
        run_id=run.id,
        report_model_hash=binding.report_model_hash,
        customer_id=run.customer_id,
        project_id=run.project_id,
        procurement_case_id=case.id,
    )
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".r8-final-pdf-", suffix=".partial", delete=False
        ) as handle:
            temporary = Path(handle.name)
        from src.modules.tender_operator_agent_demo.report_export_service import (
            _build_pdf_from_canonical,
        )

        _build_pdf_from_canonical(
            canonical, f"Анализ закупки {run.registry_number}", temporary
        )
        pdf_bytes = temporary.read_bytes()
        if not pdf_bytes.startswith(b"%PDF-"):
            raise HTTPException(422, "Frozen canonical renderer returned invalid PDF")
    finally:
        if "temporary" in locals():
            temporary.unlink(missing_ok=True)
    try:
        generation = publish_final_pdf_generation(
            customer_id=run.customer_id,
            project_id=run.project_id,
            procurement_case_id=case.id,
            run_id=run.id,
            run_result_id=binding.id,
            registry_number=run.registry_number,
            source_analysis_run_id=binding.source_analysis_run_id,
            run_namespace_key=run.artifact_key,
            artifact_key=identity.artifact_key,
            renderer_version=identity.renderer_version,
            requirements_storage_key=binding.requirements_storage_key,
            requirements_file_sha256=binding.requirements_file_sha256,
            canonical_report_storage_key=binding.canonical_report_storage_key,
            canonical_report_file_sha256=binding.canonical_report_file_sha256,
            binding_manifest_storage_key=binding.binding_manifest_storage_key,
            binding_manifest_file_sha256=binding.binding_manifest_file_sha256,
            source_graph_hash=binding.source_graph_hash,
            source_graph_hash_algorithm=binding.source_graph_hash_algorithm,
            production_model_hash=binding.production_model_hash,
            report_model_hash=binding.report_model_hash,
            pdf_bytes=pdf_bytes,
        )
    except FinalPdfArtifactConflictError as exc:
        raise HTTPException(409, "Immutable final PDF conflicts with this run") from exc
    except FinalPdfArtifactError as exc:
        raise HTTPException(422, "Final PDF cannot be published safely") from exc
    artifact = PilotArtifact(
        customer_id=run.customer_id,
        project_id=run.project_id,
        procurement_case_id=case.id,
        run_id=run.id,
        run_result_id=binding.id,
        artifact_type=_ARTIFACT_TYPE,
        artifact_key=identity.artifact_key,
        report_model_hash=binding.report_model_hash,
        source_graph_hash=binding.source_graph_hash,
        renderer_version=identity.renderer_version,
        manifest_relative_path=generation.manifest_relative_path,
        manifest_file_sha256=generation.manifest_file_sha256,
        verification_policy_version=generation.verification_policy_version,
        pdf_relative_path=generation.pdf_relative_path,
        pdf_sha256=generation.pdf_sha256,
        byte_size=generation.byte_size,
        status="published",
    )
    try:
        with session.begin_nested():
            session.add(artifact)
            session.flush()
    except IntegrityError:
        # A concurrent request may have committed the only permitted DB row
        # after the immutable filesystem generation was already verified.
        recovered = session.scalar(
            select(PilotArtifact).where(
                PilotArtifact.run_id == run.id,
                PilotArtifact.artifact_type == _ARTIFACT_TYPE,
            )
        )
        if not recovered:
            raise HTTPException(409, "Final artifact binding conflicts")
        from src.modules.customer_pilot.artifacts import verified_pilot_artifact

        verified_pilot_artifact(run, case, binding, recovered)
        return recovered, False
    return artifact, True
