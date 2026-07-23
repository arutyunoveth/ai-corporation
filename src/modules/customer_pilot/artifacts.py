"""Trust-boundary verification for immutable R8 final PDF artifacts."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException

from src.modules.customer_pilot.artifact_snapshot import (
    FinalPdfArtifactError,
    VerifiedFinalPdfGeneration,
    VERIFICATION_POLICY_VERSION,
    derive_final_pdf_artifact_identity,
    verify_final_pdf_generation,
)
from src.modules.customer_pilot.binding_verifier import (
    RunSnapshotBindingError,
    VerifiedRunSnapshotBinding,
    verify_run_snapshot_binding,
)

# Compatibility import for deployment/tests that configure the artifact module.
from src.tender_research.config import load_config  # noqa: F401


@dataclass(frozen=True)
class VerifiedPilotArtifactBinding:
    canonical: VerifiedRunSnapshotBinding
    generation: VerifiedFinalPdfGeneration
    artifact_id: str
    artifact_key: str
    pdf_bytes: bytes
    pdf_sha256: str
    manifest_file_sha256: str
    byte_size: int
    renderer_version: str
    verification_policy_version: str
    report_model_hash: str
    source_graph_hash: str


def verify_pilot_artifact_binding(
    *, run, case, result, artifact
) -> VerifiedPilotArtifactBinding:
    """Revalidate canonical and PDF generations before every lifecycle use."""
    if not result.is_verified_snapshot_binding:
        raise HTTPException(409, "Canonical snapshot binding is incomplete")
    try:
        canonical = verify_run_snapshot_binding(run=run, case=case, binding=result)
        identity = derive_final_pdf_artifact_identity(
            registry_number=run.registry_number,
            run_id=run.id,
            report_model_hash=result.report_model_hash,
            customer_id=run.customer_id,
            project_id=run.project_id,
            procurement_case_id=case.id,
        )
        expected = {
            "customer_id": run.customer_id,
            "project_id": run.project_id,
            "procurement_case_id": case.id,
            "run_id": run.id,
            "run_result_id": result.id,
            "registry_number": run.registry_number,
            "source_analysis_run_id": result.source_analysis_run_id,
            "run_namespace_key": run.artifact_key,
            "artifact_key": identity.artifact_key,
            "artifact_type": "final_pdf",
            "renderer_version": identity.renderer_version,
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
            "pdf_relative_path": identity.pdf_relative_path,
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
        (
            artifact.customer_id,
            artifact.project_id,
            artifact.procurement_case_id,
            artifact.run_id,
            artifact.run_result_id,
        )
        != (run.customer_id, run.project_id, case.id, run.id, result.id)
        or artifact.artifact_type != "final_pdf"
        or artifact.artifact_key != identity.artifact_key
        or artifact.report_model_hash != result.report_model_hash
        or artifact.source_graph_hash != result.source_graph_hash
        or artifact.renderer_version != identity.renderer_version
        or artifact.pdf_relative_path != identity.pdf_relative_path
        or artifact.manifest_relative_path != identity.manifest_relative_path
        or artifact.manifest_relative_path != generation.manifest_relative_path
        or artifact.manifest_file_sha256 != generation.manifest_file_sha256
        or artifact.verification_policy_version != VERIFICATION_POLICY_VERSION
        or artifact.status != "published"
        or artifact.pdf_sha256 != generation.pdf_sha256
        or artifact.byte_size != generation.byte_size
        or generation.artifact_key != identity.artifact_key
        or generation.renderer_version != identity.renderer_version
        or generation.pdf_relative_path != identity.pdf_relative_path
        or generation.manifest_relative_path != identity.manifest_relative_path
    ):
        raise HTTPException(409, "Final artifact database binding is invalid")
    manifest = generation.parsed_manifest
    expected_canonical = {
        "requirements_file_sha256": canonical.requirements_file_sha256,
        "canonical_report_file_sha256": canonical.canonical_report_file_sha256,
        "binding_manifest_file_sha256": canonical.binding_manifest_file_sha256,
        "source_graph_hash": canonical.source_graph_hash,
        "source_graph_hash_algorithm": canonical.source_graph_hash_algorithm,
        "production_model_hash": canonical.production_model_hash,
        "report_model_hash": canonical.report_model_hash,
        "source_analysis_run_id": canonical.source_analysis_run_id,
    }
    if any(manifest.get(key) != value for key, value in expected_canonical.items()):
        raise HTTPException(409, "Final artifact canonical binding is invalid")
    return VerifiedPilotArtifactBinding(
        canonical,
        generation,
        artifact.id,
        identity.artifact_key,
        generation.pdf_bytes,
        generation.pdf_sha256,
        generation.manifest_file_sha256,
        generation.byte_size,
        identity.renderer_version,
        generation.verification_policy_version,
        canonical.report_model_hash,
        canonical.source_graph_hash,
    )


def verified_pilot_artifact(
    run, case, result, artifact
) -> VerifiedPilotArtifactBinding:
    """Compatibility wrapper for the sole strict artifact verification policy."""
    return verify_pilot_artifact_binding(
        run=run, case=case, result=result, artifact=artifact
    )


def verify_review_artifact_binding(
    *, review, run, case, result, artifact, verified_artifact
) -> None:
    """Approval is immutable only when it binds this exact verified artifact."""
    if (
        review.customer_id != run.customer_id
        or review.project_id != run.project_id
        or review.procurement_case_id != case.id
        or review.run_id != run.id
        or review.artifact_id != artifact.id
        or review.artifact_key != artifact.artifact_key
        or review.pdf_sha256 != verified_artifact.pdf_sha256
        or review.renderer_version != verified_artifact.renderer_version
        or review.report_model_hash != result.report_model_hash
        or review.source_graph_hash != result.source_graph_hash
        or review.artifact_hashes != {"pdf": verified_artifact.pdf_sha256}
        or review.immutable_at is None
        or review.verdict not in {"approved", "approved_with_notes"}
    ):
        raise HTTPException(409, "Immutable review artifact binding is invalid")


def verified_pdf_manifest(run, case) -> dict:
    raise HTTPException(
        409, "Use a persisted PilotArtifact for R8 artifact verification"
    )
