"""Atomic immutable publication and verification for final R8 PDF artifacts.

The PDF is deliberately published as a directory generation, rather than as
two independently replaced files.  This keeps the artifact trust boundary
equivalent to the canonical snapshot boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from src.modules.customer_pilot.canonical_snapshot import (
    CanonicalSnapshotStorageError,
    _fsync_dir,
    _lstat,
    _read_regular,
    _run_lock,
    _safe_namespace,
    _safe_remove_tree,
)

MANIFEST_VERSION = "r8-final-pdf-binding-v1"
VERIFICATION_POLICY_VERSION = "r8-final-pdf-verifier-v1"
PATH_SCOPE = "data-root-relative"
EXACT_FILE_SET = ["final.pdf", "artifact.manifest.json"]
_HASH_LENGTH = 64
_MANIFEST_KEYS = {
    "manifest_version",
    "verification_policy_version",
    "path_scope",
    "customer_id",
    "project_id",
    "procurement_case_id",
    "run_id",
    "run_result_id",
    "registry_number",
    "source_analysis_run_id",
    "run_namespace_key",
    "artifact_key",
    "artifact_type",
    "renderer_version",
    "requirements_storage_key",
    "requirements_file_sha256",
    "canonical_report_storage_key",
    "canonical_report_file_sha256",
    "binding_manifest_storage_key",
    "binding_manifest_file_sha256",
    "source_graph_hash",
    "source_graph_hash_algorithm",
    "production_model_hash",
    "report_model_hash",
    "pdf_relative_path",
    "pdf_sha256",
    "byte_size",
    "exact_file_set",
    "created_at",
}


class FinalPdfArtifactError(RuntimeError):
    pass


class FinalPdfArtifactContractError(FinalPdfArtifactError):
    pass


class FinalPdfArtifactStorageError(FinalPdfArtifactError):
    pass


class FinalPdfArtifactConflictError(FinalPdfArtifactError):
    pass


@dataclass(frozen=True)
class PublishedFinalPdfGeneration:
    artifact_directory: Path
    pdf_path: Path
    manifest_path: Path
    pdf_relative_path: str
    manifest_relative_path: str
    pdf_sha256: str
    manifest_file_sha256: str
    byte_size: int
    manifest: dict
    manifest_bytes: bytes
    verification_policy_version: str
    created_at: str
    idempotent: bool


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _manifest_bytes(value: dict) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _error_storage(exc: OSError) -> FinalPdfArtifactStorageError:
    return FinalPdfArtifactStorageError(
        "Final PDF artifact filesystem operation failed"
    )


def _validate_manifest(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != _MANIFEST_KEYS:
        raise FinalPdfArtifactContractError("Final PDF manifest schema is invalid")
    if (
        value["manifest_version"] != MANIFEST_VERSION
        or value["verification_policy_version"] != VERIFICATION_POLICY_VERSION
        or value["path_scope"] != PATH_SCOPE
        or value["exact_file_set"] != EXACT_FILE_SET
    ):
        raise FinalPdfArtifactContractError("Final PDF manifest policy is invalid")
    for key in (
        "requirements_file_sha256",
        "canonical_report_file_sha256",
        "binding_manifest_file_sha256",
        "source_graph_hash",
        "production_model_hash",
        "report_model_hash",
        "pdf_sha256",
    ):
        if (
            not isinstance(value[key], str)
            or len(value[key]) != _HASH_LENGTH
            or any(c not in "0123456789abcdef" for c in value[key])
        ):
            raise FinalPdfArtifactContractError("Final PDF manifest hash is invalid")
    if not isinstance(value["byte_size"], int) or value["byte_size"] <= 0:
        raise FinalPdfArtifactContractError("Final PDF manifest byte size is invalid")
    try:
        created = datetime.fromisoformat(value["created_at"])
    except (TypeError, ValueError) as exc:
        raise FinalPdfArtifactContractError(
            "Final PDF manifest timestamp is invalid"
        ) from exc
    if created.tzinfo is None or created.utcoffset() is None:
        raise FinalPdfArtifactContractError("Final PDF manifest timestamp is invalid")
    return value


def _read_generation(final: Path, expected: dict) -> PublishedFinalPdfGeneration:
    try:
        mode = _lstat(final).st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise FinalPdfArtifactStorageError("Final PDF artifact directory is unsafe")
        names = sorted(path.name for path in final.iterdir())
    except FinalPdfArtifactError:
        raise
    except (OSError, CanonicalSnapshotStorageError) as exc:
        raise FinalPdfArtifactStorageError("Final PDF artifact is unreadable") from exc
    if names != sorted(EXACT_FILE_SET):
        raise FinalPdfArtifactContractError("Final PDF artifact file set is invalid")
    try:
        pdf = _read_regular(final / "final.pdf")
        manifest_bytes = _read_regular(final / "artifact.manifest.json")
        payload = _validate_manifest(json.loads(manifest_bytes))
    except FinalPdfArtifactError:
        raise
    except (
        CanonicalSnapshotStorageError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise FinalPdfArtifactContractError("Final PDF artifact is malformed") from exc
    if (
        not pdf.startswith(b"%PDF-")
        or _sha(pdf) != payload["pdf_sha256"]
        or len(pdf) != payload["byte_size"]
    ):
        raise FinalPdfArtifactContractError("Final PDF bytes do not match manifest")
    if any(payload.get(key) != value for key, value in expected.items()):
        raise FinalPdfArtifactConflictError("Immutable final PDF artifact conflicts")
    return PublishedFinalPdfGeneration(
        final,
        final / "final.pdf",
        final / "artifact.manifest.json",
        payload["pdf_relative_path"],
        str(Path(payload["pdf_relative_path"]).with_name("artifact.manifest.json")),
        payload["pdf_sha256"],
        _sha(manifest_bytes),
        len(pdf),
        payload,
        manifest_bytes,
        payload["verification_policy_version"],
        payload["created_at"],
        True,
    )


def publish_final_pdf_generation(
    *,
    customer_id: str,
    project_id: str,
    procurement_case_id: str,
    run_id: str,
    run_result_id: str,
    registry_number: str,
    source_analysis_run_id: str,
    run_namespace_key: str,
    artifact_key: str,
    renderer_version: str,
    requirements_storage_key: str,
    requirements_file_sha256: str,
    canonical_report_storage_key: str,
    canonical_report_file_sha256: str,
    binding_manifest_storage_key: str,
    binding_manifest_file_sha256: str,
    source_graph_hash: str,
    source_graph_hash_algorithm: str,
    production_model_hash: str,
    report_model_hash: str,
    pdf_bytes: bytes,
    now_factory: Callable[[], datetime] = lambda: datetime.now(UTC),
    fault: Callable[[str], None] | None = None,
) -> PublishedFinalPdfGeneration:
    """Publish exact renderer bytes once; existing immutable output is verified."""
    if not isinstance(pdf_bytes, bytes) or not pdf_bytes.startswith(b"%PDF-"):
        raise FinalPdfArtifactContractError(
            "Frozen canonical renderer returned invalid PDF"
        )
    values = (
        customer_id,
        project_id,
        procurement_case_id,
        run_id,
        run_result_id,
        registry_number,
        source_analysis_run_id,
        run_namespace_key,
        artifact_key,
        renderer_version,
        requirements_storage_key,
        canonical_report_storage_key,
        binding_manifest_storage_key,
        source_graph_hash_algorithm,
    )
    if any(not isinstance(value, str) or not value for value in values):
        raise FinalPdfArtifactContractError("Final PDF artifact ownership is invalid")
    hashes = (
        requirements_file_sha256,
        canonical_report_file_sha256,
        binding_manifest_file_sha256,
        source_graph_hash,
        production_model_hash,
        report_model_hash,
    )
    if any(
        not isinstance(value, str)
        or len(value) != _HASH_LENGTH
        or any(c not in "0123456789abcdef" for c in value)
        for value in hashes
    ):
        raise FinalPdfArtifactContractError("Final PDF artifact binding is invalid")
    if source_graph_hash_algorithm != "sha256-json-c14n-v1":
        raise FinalPdfArtifactContractError("Final PDF source graph policy is invalid")
    try:
        run_root = _safe_namespace(customer_id, project_id, procurement_case_id, run_id)
    except (CanonicalSnapshotStorageError, RuntimeError) as exc:
        raise FinalPdfArtifactStorageError("Final PDF namespace is unsafe") from exc
    base = (
        Path("customer-pilot")
        / customer_id
        / project_id
        / procurement_case_id
        / run_id
        / "artifacts"
        / artifact_key
    )
    pdf_relative, manifest_relative = (
        str(base / "final.pdf"),
        str(base / "artifact.manifest.json"),
    )
    expected = {
        "customer_id": customer_id,
        "project_id": project_id,
        "procurement_case_id": procurement_case_id,
        "run_id": run_id,
        "run_result_id": run_result_id,
        "registry_number": registry_number,
        "source_analysis_run_id": source_analysis_run_id,
        "run_namespace_key": run_namespace_key,
        "artifact_key": artifact_key,
        "artifact_type": "final_pdf",
        "renderer_version": renderer_version,
        "requirements_storage_key": requirements_storage_key,
        "requirements_file_sha256": requirements_file_sha256,
        "canonical_report_storage_key": canonical_report_storage_key,
        "canonical_report_file_sha256": canonical_report_file_sha256,
        "binding_manifest_storage_key": binding_manifest_storage_key,
        "binding_manifest_file_sha256": binding_manifest_file_sha256,
        "source_graph_hash": source_graph_hash,
        "source_graph_hash_algorithm": source_graph_hash_algorithm,
        "production_model_hash": production_model_hash,
        "report_model_hash": report_model_hash,
        "pdf_relative_path": pdf_relative,
        "pdf_sha256": _sha(pdf_bytes),
        "byte_size": len(pdf_bytes),
    }
    artifacts_root = run_root / "artifacts"
    with _run_lock(run_root):
        try:
            if artifacts_root.exists():
                mode = _lstat(artifacts_root).st_mode
                if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                    raise FinalPdfArtifactStorageError(
                        "Final PDF artifact namespace is unsafe"
                    )
            else:
                artifacts_root.mkdir(mode=0o750)
            final = artifacts_root / artifact_key
            if final.exists():
                return _read_generation(final, expected)
            temp = Path(
                tempfile.mkdtemp(
                    prefix=f".artifact.{artifact_key}.partial.", dir=artifacts_root
                )
            )
            payload = {
                "manifest_version": MANIFEST_VERSION,
                "verification_policy_version": VERIFICATION_POLICY_VERSION,
                "path_scope": PATH_SCOPE,
                **expected,
                "exact_file_set": EXACT_FILE_SET,
                "created_at": now_factory().astimezone(UTC).isoformat(),
            }
            manifest_bytes = _manifest_bytes(payload)
            for name, content, point in (
                ("final.pdf", pdf_bytes, "after_pdf_written"),
                ("artifact.manifest.json", manifest_bytes, "after_manifest_written"),
            ):
                with (temp / name).open("xb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                if fault:
                    fault(point)
            if fault:
                fault("before_temp_directory_fsync")
            _fsync_dir(temp)
            # Verify the staging generation before a single directory rename.
            generated = _read_generation(temp, expected)
            if generated.idempotent is not True:
                raise FinalPdfArtifactContractError(
                    "Final PDF staging verification failed"
                )
            if fault:
                fault("before_rename")
            os.replace(temp, final)
            if fault:
                fault("after_rename")
            if fault:
                fault("before_parent_fsync")
            _fsync_dir(artifacts_root)
        except FinalPdfArtifactError:
            if "temp" in locals() and temp.exists():
                _safe_remove_tree(temp)
            raise
        except (OSError, CanonicalSnapshotStorageError) as exc:
            if "temp" in locals() and temp.exists():
                _safe_remove_tree(temp)
            raise FinalPdfArtifactStorageError("Final PDF publication failed") from exc
    return PublishedFinalPdfGeneration(
        final,
        final / "final.pdf",
        final / "artifact.manifest.json",
        pdf_relative,
        manifest_relative,
        expected["pdf_sha256"],
        _sha(manifest_bytes),
        len(pdf_bytes),
        payload,
        manifest_bytes,
        VERIFICATION_POLICY_VERSION,
        payload["created_at"],
        False,
    )


def verify_final_pdf_generation(
    *,
    customer_id: str,
    project_id: str,
    procurement_case_id: str,
    run_id: str,
    expected: dict,
) -> PublishedFinalPdfGeneration:
    try:
        run_root = _safe_namespace(customer_id, project_id, procurement_case_id, run_id)
    except (CanonicalSnapshotStorageError, RuntimeError) as exc:
        raise FinalPdfArtifactStorageError("Final PDF namespace is unsafe") from exc
    artifact_key = expected.get("artifact_key")
    if not isinstance(artifact_key, str):
        raise FinalPdfArtifactContractError("Final PDF artifact key is invalid")
    return _read_generation(run_root / "artifacts" / artifact_key, expected)
