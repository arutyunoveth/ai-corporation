"""Trust-boundary verification for immutable R8 final PDF artifacts."""

from __future__ import annotations

from fastapi import HTTPException

from src.modules.customer_pilot.artifact_snapshot import (
    FinalPdfArtifactError,
    VERIFICATION_POLICY_VERSION,
    verify_final_pdf_generation,
)
from src.modules.customer_pilot.binding_verifier import (
    RunSnapshotBindingError,
    verify_run_snapshot_binding,
)

# Compatibility import for deployment/tests that configure the artifact module.
from src.tender_research.config import load_config  # noqa: F401


def verified_pilot_artifact(run, case, result, artifact) -> dict:
    """Revalidate canonical and PDF generations before every lifecycle use."""
    if not result.is_verified_snapshot_binding:
        raise HTTPException(409, "Canonical snapshot binding is incomplete")
    try:
        verify_run_snapshot_binding(run=run, case=case, binding=result)
        expected = {
            "customer_id": run.customer_id,
            "project_id": run.project_id,
            "procurement_case_id": case.id,
            "run_id": run.id,
            "run_result_id": result.id,
            "registry_number": run.registry_number,
            "source_analysis_run_id": result.source_analysis_run_id,
            "run_namespace_key": run.artifact_key,
            "artifact_key": artifact.artifact_key,
            "artifact_type": "final_pdf",
            "renderer_version": artifact.renderer_version,
            "requirements_storage_key": result.requirements_storage_key,
            "requirements_file_sha256": result.requirements_file_sha256,
            "canonical_report_storage_key": result.canonical_report_storage_key,
            "canonical_report_file_sha256": result.canonical_report_file_sha256,
            "binding_manifest_storage_key": result.binding_manifest_storage_key,
            "binding_manifest_file_sha256": result.binding_manifest_file_sha256,
            "source_graph_hash": result.source_graph_hash,
            "source_graph_hash_algorithm": result.source_graph_hash_algorithm,
            "production_model_hash": result.production_model_hash,
            "report_model_hash": result.report_model_hash,
            "pdf_relative_path": artifact.pdf_relative_path,
            "pdf_sha256": artifact.pdf_sha256,
            "byte_size": artifact.byte_size,
        }
        generation = verify_final_pdf_generation(
            customer_id=run.customer_id,
            project_id=run.project_id,
            procurement_case_id=case.id,
            run_id=run.id,
            expected=expected,
        )
    except (RunSnapshotBindingError, FinalPdfArtifactError) as exc:
        raise HTTPException(409, "Final artifact trust binding is invalid") from exc
    if (
        artifact.manifest_relative_path != generation.manifest_relative_path
        or artifact.manifest_file_sha256 != generation.manifest_file_sha256
        or artifact.verification_policy_version != VERIFICATION_POLICY_VERSION
        or artifact.status != "published"
    ):
        raise HTTPException(409, "Final artifact database binding is invalid")
    return generation.manifest


def verified_pdf_manifest(run, case) -> dict:
    raise HTTPException(
        409, "Use a persisted PilotArtifact for R8 artifact verification"
    )
