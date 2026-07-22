"""Verification for server-published R8 customer artifacts only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import HTTPException

from src.tender_research.config import load_config

REQUIRED_MANIFEST_KEYS = {
    "customer_id",
    "project_id",
    "procurement_case_id",
    "run_id",
    "run_result_id",
    "registry_number",
    "run_namespace_key",
    "artifact_key",
    "artifact_type",
    "report_model_hash",
    "source_graph_hash",
    "renderer_version",
    "pdf_relative_path",
    "canonical_report_storage_key",
    "canonical_report_file_sha256",
    "binding_manifest_storage_key",
    "binding_manifest_file_sha256",
    "production_model_hash",
    "pdf_sha256",
    "byte_size",
    "created_at",
}


def _safe_file(relative: str) -> Path:
    root = Path(load_config().data_dir).resolve()
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise HTTPException(422, "Artifact path is unsafe")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise HTTPException(422, "Artifact path is unsafe") from exc
    raw = root / candidate
    if raw.is_symlink() or not raw.is_file():
        raise HTTPException(409, "Artifact is missing or unsafe")
    return raw


def verified_pilot_artifact(
    run, case, result, artifact, *, manifest_path: str | None = None
) -> dict:
    """Verify every DB and manifest ownership edge and inspect PDF bytes once."""
    if not result.is_verified_snapshot_binding:
        raise HTTPException(409, "Canonical snapshot binding is incomplete")
    relative_manifest = manifest_path or (
        artifact.manifest_relative_path if artifact else None
    )
    if not relative_manifest:
        raise HTTPException(409, "Final artifact is not registered")
    try:
        raw_manifest = _safe_file(relative_manifest)
        payload = json.loads(raw_manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(
            409, "Final artifact manifest is missing or invalid"
        ) from exc
    if not isinstance(payload, dict) or set(payload) != REQUIRED_MANIFEST_KEYS:
        raise HTTPException(422, "Final artifact manifest is incomplete")
    expected = {
        "customer_id": run.customer_id,
        "project_id": run.project_id,
        "procurement_case_id": case.id,
        "run_id": run.id,
        "run_result_id": result.id,
        "registry_number": run.registry_number,
        "run_namespace_key": run.artifact_key,
        "report_model_hash": result.report_model_hash,
        "source_graph_hash": result.source_graph_hash,
        "canonical_report_storage_key": result.canonical_report_storage_key,
        "canonical_report_file_sha256": result.canonical_report_file_sha256,
        "binding_manifest_storage_key": result.binding_manifest_storage_key,
        "binding_manifest_file_sha256": result.binding_manifest_file_sha256,
        "production_model_hash": result.production_model_hash,
        "artifact_type": "final_pdf",
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise HTTPException(409, "Final artifact does not belong to this customer run")
    if artifact:
        fields = (
            "artifact_key",
            "report_model_hash",
            "source_graph_hash",
            "renderer_version",
            "pdf_relative_path",
            "pdf_sha256",
            "byte_size",
        )
        if any(payload.get(key) != getattr(artifact, key) for key in fields):
            raise HTTPException(409, "Final artifact database binding is invalid")
        if relative_manifest != artifact.manifest_relative_path:
            raise HTTPException(409, "Final artifact manifest path is invalid")
        if (
            artifact.customer_id,
            artifact.project_id,
            artifact.procurement_case_id,
            artifact.run_id,
            artifact.run_result_id,
        ) != (run.customer_id, run.project_id, case.id, run.id, result.id):
            raise HTTPException(409, "Final artifact ownership is invalid")
    pdf = _safe_file(payload["pdf_relative_path"])
    pdf_bytes = pdf.read_bytes()
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(422, "Final artifact is not a PDF")
    if (
        len(pdf_bytes) != payload["byte_size"]
        or hashlib.sha256(pdf_bytes).hexdigest() != payload["pdf_sha256"]
    ):
        raise HTTPException(409, "Final artifact PDF hash does not match manifest")
    return payload


def verified_pdf_manifest(run, case) -> dict:
    """Compatibility name retained for callers; R8 requires a persisted binding."""
    raise HTTPException(
        409, "Use a persisted PilotArtifact for R8 final artifact verification"
    )
