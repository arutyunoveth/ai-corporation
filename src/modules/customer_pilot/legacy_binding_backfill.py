"""Explicit, fail-closed conversion of pre-096 immutable canonical bindings."""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from src.modules.customer_pilot.artifact_snapshot import (
    EXACT_FILE_SET as ARTIFACT_FILE_SET,
)
from src.modules.customer_pilot.artifact_snapshot import (
    VERIFICATION_POLICY_VERSION as ARTIFACT_POLICY_VERSION,
)
from src.modules.customer_pilot.canonical_snapshot import (
    EXACT_FILE_SET,
    SOURCE_GRAPH_HASH_ALGORITHM,
    VERIFICATION_POLICY_VERSION,
)
from src.modules.procurement_analysis.canonical_persistence import (
    verify_canonical_bytes,
)


@dataclass(frozen=True)
class LegacyBackfillResult:
    status: str
    changed_fields: tuple[str, ...]
    verified_identities: dict[str, str]
    error_category: str | None
    mutation_performed: bool


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _regular(path: Path) -> bytes:
    value = path.lstat()
    if stat.S_ISLNK(value.st_mode) or not stat.S_ISREG(value.st_mode):
        raise ValueError("unsafe_filesystem")
    return path.read_bytes()


def _directory(path: Path) -> None:
    value = path.lstat()
    if stat.S_ISLNK(value.st_mode) or not stat.S_ISDIR(value.st_mode):
        raise ValueError("unsafe_filesystem")


def _result(status: str, error: str | None = None, identities: dict | None = None):
    return LegacyBackfillResult(status, (), identities or {}, error, False)


def backfill_legacy_run_binding(*, session, run, case, run_result, artifact, data_root):
    """Backfill only a complete immutable 095 snapshot; never repair it.

    All validation is performed before assigning a mapped value, so errors leave
    both the caller's transaction and the filesystem untouched.
    """
    # PostgreSQL callers lock result first, then artifact.  Re-reading after the
    # lock makes a concurrent caller observe the completed binding instead of
    # racing to write the same nullable columns.
    if hasattr(session, "scalar"):
        from src.modules.customer_pilot.models import PilotArtifact, PilotRunResult

        locked_result = session.scalar(
            select(PilotRunResult)
            .where(PilotRunResult.id == run_result.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        locked_artifact = session.scalar(
            select(PilotArtifact)
            .where(PilotArtifact.id == artifact.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if locked_result is None or locked_artifact is None:
            return _result("CONFLICT", "missing_locked_row")
        run_result, artifact = locked_result, locked_artifact
    if (
        run.customer_id,
        run.project_id,
        case.customer_id,
        case.project_id,
        run_result.customer_id,
        run_result.project_id,
        run_result.procurement_case_id,
        run_result.run_id,
        artifact.customer_id,
        artifact.project_id,
        artifact.procurement_case_id,
        artifact.run_id,
        artifact.run_result_id,
    ) != (
        run.customer_id,
        run.project_id,
        run.customer_id,
        run.project_id,
        run.customer_id,
        run.project_id,
        case.id,
        run.id,
        run.customer_id,
        run.project_id,
        case.id,
        run.id,
        run_result.id,
    ):
        return _result("CONFLICT", "ownership_mismatch")

    new_fields = (
        "requirements_storage_key",
        "requirements_file_sha256",
        "canonical_report_file_sha256",
        "binding_manifest_storage_key",
        "binding_manifest_file_sha256",
        "source_graph_hash_algorithm",
        "report_model_hash",
        "verification_policy_version",
    )
    if all(getattr(run_result, field, None) is not None for field in new_fields):
        from src.modules.customer_pilot.binding_verifier import (
            RunSnapshotBindingError,
            verify_run_snapshot_binding,
        )

        try:
            verify_run_snapshot_binding(run=run, case=case, binding=run_result)
        except RunSnapshotBindingError:
            return _result("CONFLICT", "invalid_verified_binding")
        return _result("ALREADY_VERIFIED")
    if any(getattr(run_result, field, None) is not None for field in new_fields):
        return _result("CONFLICT", "partial_preexisting_binding")

    root = Path(data_root)
    analysis = (
        root
        / "customer-pilot"
        / run.customer_id
        / run.project_id
        / case.id
        / run.id
        / "analysis"
    )
    try:
        for item in (root, root / "customer-pilot", analysis.parent, analysis):
            _directory(item)
        if {path.name for path in analysis.iterdir()} != set(EXACT_FILE_SET):
            return _result("INCOMPLETE", "exact_snapshot_file_set")
        requirements = _regular(analysis / "requirements.json")
        report = _regular(analysis / "canonical_report.json")
        manifest_bytes = _regular(analysis / "canonical-binding.manifest.json")
        verified = verify_canonical_bytes(
            requirements_bytes=requirements, canonical_report_bytes=report
        )
        manifest = json.loads(manifest_bytes)
    except FileNotFoundError:
        return _result("INCOMPLETE", "missing_snapshot_file")
    except (OSError, ValueError, json.JSONDecodeError):
        return _result("CONFLICT", "invalid_snapshot")

    expected_base = str(
        Path("customer-pilot")
        / run.customer_id
        / run.project_id
        / case.id
        / run.id
        / "analysis"
    )
    identities = {
        "requirements_storage_key": f"{expected_base}/requirements.json",
        "requirements_file_sha256": verified.requirements_file_sha256,
        "canonical_report_file_sha256": verified.canonical_report_file_sha256,
        "binding_manifest_storage_key": f"{expected_base}/canonical-binding.manifest.json",
        "binding_manifest_file_sha256": _sha(manifest_bytes),
        "source_graph_hash_algorithm": SOURCE_GRAPH_HASH_ALGORITHM,
        "report_model_hash": verified.report_model_hash,
        "verification_policy_version": VERIFICATION_POLICY_VERSION,
    }
    expected_manifest = {
        "customer_id": run.customer_id,
        "project_id": run.project_id,
        "procurement_case_id": case.id,
        "run_id": run.id,
        "registry_number": run.registry_number,
        "source_analysis_run_id": run_result.source_analysis_run_id,
        "source_graph_hash": run_result.source_graph_hash,
        "source_graph_hash_algorithm": SOURCE_GRAPH_HASH_ALGORITHM,
        "production_model_hash": run_result.production_model_hash,
        "report_model_hash": verified.report_model_hash,
        "requirements_relative_path": identities["requirements_storage_key"],
        "requirements_file_sha256": identities["requirements_file_sha256"],
        "canonical_report_relative_path": run_result.canonical_report_storage_key,
        "canonical_report_file_sha256": identities["canonical_report_file_sha256"],
        "exact_file_set": EXACT_FILE_SET,
        "verification_policy_version": VERIFICATION_POLICY_VERSION,
    }
    if any(manifest.get(key) != value for key, value in expected_manifest.items()):
        return _result("CONFLICT", "canonical_identity_conflict", identities)
    if run_result.canonical_report_hash != verified.report_model_hash:
        return _result("CONFLICT", "legacy_report_hash_conflict", identities)
    artifact_dir = root / artifact.manifest_relative_path
    try:
        _directory(artifact_dir)
        if {path.name for path in artifact_dir.iterdir()} != set(ARTIFACT_FILE_SET):
            return _result("CONFLICT", "artifact_file_set")
        artifact_manifest = _regular(artifact_dir / "artifact.manifest.json")
    except (FileNotFoundError, OSError, ValueError):
        return _result("CONFLICT", "artifact_snapshot_invalid")
    values = {
        **identities,
        "manifest_file_sha256": _sha(artifact_manifest),
        "artifact_verification_policy_version": ARTIFACT_POLICY_VERSION,
    }
    for field in new_fields:
        setattr(run_result, field, values[field])
    artifact.manifest_file_sha256 = values["manifest_file_sha256"]
    artifact.verification_policy_version = values[
        "artifact_verification_policy_version"
    ]
    session.flush()
    return LegacyBackfillResult(
        "BACKFILLED",
        tuple((*new_fields, "manifest_file_sha256", "verification_policy_version")),
        values,
        None,
        True,
    )
