"""Server-side verification of immutable R7-style PDF manifests for R8 runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import HTTPException

from src.tender_research.config import load_config

REQUIRED_MANIFEST_KEYS = {
    "run_id",
    "registry_number",
    "artifact_key",
    "report_model_hash",
    "renderer_version",
    "pdf_relative_path",
    "pdf_sha256",
    "byte_size",
}


def verified_pdf_manifest(run, case) -> dict:
    """Read an artifact manifest named by trusted persisted run metadata only."""
    try:
        metadata = json.loads(run.metadata_json or "{}")
        relative_manifest = metadata["artifact_manifest_path"]
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            409, "Final artifact manifest is not registered for this run"
        ) from exc
    root = Path(load_config().data_dir).resolve()
    manifest_path = (root / relative_manifest).resolve()
    try:
        manifest_path.relative_to(root)
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(
            409, "Final artifact manifest is missing or invalid"
        ) from exc
    if not REQUIRED_MANIFEST_KEYS.issubset(payload):
        raise HTTPException(422, "Final artifact manifest is incomplete")
    expected = {
        "run_id": run.id,
        "registry_number": run.registry_number,
        "artifact_key": run.artifact_key,
    }
    if any(payload[key] != value for key, value in expected.items()):
        raise HTTPException(
            409, "Final artifact manifest does not belong to this customer run"
        )
    pdf_path = (root / payload["pdf_relative_path"]).resolve()
    try:
        pdf_path.relative_to(root)
    except ValueError as exc:
        raise HTTPException(422, "Final artifact PDF path is unsafe") from exc
    if not pdf_path.is_file() or pdf_path.stat().st_size != payload["byte_size"]:
        raise HTTPException(409, "Final artifact PDF is missing or changed")
    if pdf_path.read_bytes()[:5] != b"%PDF-":
        raise HTTPException(422, "Final artifact is not a PDF")
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if digest != payload["pdf_sha256"]:
        raise HTTPException(409, "Final artifact PDF hash does not match manifest")
    return payload
