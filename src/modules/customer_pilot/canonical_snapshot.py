"""Atomic customer-scoped publication of already verified canonical bytes."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.modules.procurement_analysis.canonical_persistence import PersistedCanonicalOutputs, SOURCE_GRAPH_HASH_ALGORITHM
from src.tender_research.config import load_config

_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_VERSION = "r8-canonical-binding-v1"
VERIFICATION_POLICY_VERSION = "r8-frozen-canonical-verifier-v1"
PATH_SCOPE = "data-root-relative"
EXACT_FILE_SET = ["requirements.json", "canonical_report.json", "canonical-binding.manifest.json"]

class CanonicalSnapshotError(RuntimeError): pass
class CanonicalSnapshotContractError(CanonicalSnapshotError): pass
class CanonicalSnapshotStorageError(CanonicalSnapshotError): pass
class CanonicalSnapshotConflictError(CanonicalSnapshotError): pass

@dataclass(frozen=True)
class PublishedCanonicalSnapshot:
    analysis_directory: Path; requirements_path: Path; canonical_report_path: Path; binding_manifest_path: Path
    requirements_relative_path: str; canonical_report_relative_path: str; binding_manifest_relative_path: str
    requirements_file_sha256: str; canonical_report_file_sha256: str; binding_manifest_file_sha256: str
    source_graph_hash: str; source_graph_hash_algorithm: str; production_model_hash: str; report_model_hash: str
    manifest: dict; manifest_bytes: bytes; idempotent: bool

def _root(*values: str) -> Path:
    if any(not isinstance(value, str) or not _SAFE.fullmatch(value) for value in values): raise CanonicalSnapshotContractError("Unsafe customer snapshot segment")
    root = Path(load_config().data_dir).resolve()
    path = root.joinpath("customer-pilot", *values)
    for parent in [root, *[root.joinpath("customer-pilot", *values[:i]) for i in range(0, len(values) + 1)]]:
        if parent.exists() and (parent.is_symlink() or not parent.is_dir()): raise CanonicalSnapshotStorageError("Unsafe customer snapshot directory")
    return path

def _validate_bundle(verified: PersistedCanonicalOutputs) -> None:
    if not isinstance(verified, PersistedCanonicalOutputs): raise CanonicalSnapshotContractError("Verified canonical bundle is required")
    for value, digest in ((verified.requirements_bytes, verified.requirements_file_sha256), (verified.canonical_report_bytes, verified.canonical_report_file_sha256)):
        if not isinstance(value, bytes) or not value or hashlib.sha256(value).hexdigest() != digest: raise CanonicalSnapshotContractError("Verified canonical bytes do not match identity")
    if any(not isinstance(value, str) or not _HASH.fullmatch(value) for value in (verified.source_graph_hash, verified.production_model_hash, verified.report_model_hash)) or SOURCE_GRAPH_HASH_ALGORITHM != "sha256-json-c14n-v1":
        raise CanonicalSnapshotContractError("Verified canonical identities are invalid")

def _validate_manifest(payload: object) -> dict:
    required = {"manifest_version","verification_policy_version","path_scope","customer_id","project_id","procurement_case_id","run_id","registry_number","source_analysis_run_id","source_graph_hash","source_graph_hash_algorithm","production_model_hash","report_model_hash","requirements_relative_path","requirements_file_sha256","canonical_report_relative_path","canonical_report_file_sha256","exact_file_set","created_at"}
    if not isinstance(payload, dict) or set(payload) != required: raise CanonicalSnapshotContractError("Snapshot manifest schema is invalid")
    if payload["manifest_version"] != MANIFEST_VERSION or payload["verification_policy_version"] != VERIFICATION_POLICY_VERSION or payload["path_scope"] != PATH_SCOPE or payload["source_graph_hash_algorithm"] != SOURCE_GRAPH_HASH_ALGORITHM or payload["exact_file_set"] != EXACT_FILE_SET: raise CanonicalSnapshotContractError("Snapshot manifest policy is invalid")
    try:
        parsed = datetime.fromisoformat(payload["created_at"])
    except (TypeError, ValueError) as exc: raise CanonicalSnapshotContractError("Snapshot manifest timestamp is invalid") from exc
    if parsed.tzinfo is None: raise CanonicalSnapshotContractError("Snapshot manifest timestamp is not timezone aware")
    return payload

def publish_canonical_snapshot(*, customer_id: str, project_id: str, procurement_case_id: str, run_id: str, registry_number: str, source_analysis_run_id: str | None, verified: PersistedCanonicalOutputs, created_at: datetime | None = None) -> PublishedCanonicalSnapshot:
    _validate_bundle(verified)
    run_root = _root(customer_id, project_id, procurement_case_id, run_id); run_root.mkdir(parents=True, exist_ok=True)
    final = run_root / "analysis"; manifest_name = "canonical-binding.manifest.json"
    base_rel = Path("customer-pilot") / customer_id / project_id / procurement_case_id / run_id / "analysis"
    req_rel, report_rel, manifest_rel = str(base_rel / "requirements.json"), str(base_rel / "canonical_report.json"), str(base_rel / manifest_name)
    if final.exists():
        if final.is_symlink() or not final.is_dir(): raise CanonicalSnapshotStorageError("Existing analysis snapshot is unsafe")
        try:
            existing = (final / manifest_name).read_bytes(); payload = _validate_manifest(json.loads(existing))
            expected = {"customer_id":customer_id,"project_id":project_id,"procurement_case_id":procurement_case_id,"run_id":run_id,"registry_number":registry_number,"source_analysis_run_id":source_analysis_run_id,"source_graph_hash":verified.source_graph_hash,"source_graph_hash_algorithm":SOURCE_GRAPH_HASH_ALGORITHM,"production_model_hash":verified.production_model_hash,"report_model_hash":verified.report_model_hash,"requirements_file_sha256":verified.requirements_file_sha256,"canonical_report_file_sha256":verified.canonical_report_file_sha256}
            if (final / "requirements.json").read_bytes() == verified.requirements_bytes and (final / "canonical_report.json").read_bytes() == verified.canonical_report_bytes and all(payload.get(k) == v for k, v in expected.items()):
                return PublishedCanonicalSnapshot(final, final/"requirements.json", final/"canonical_report.json", final/manifest_name, req_rel, report_rel, manifest_rel, verified.requirements_file_sha256, verified.canonical_report_file_sha256, hashlib.sha256(existing).hexdigest(), verified.source_graph_hash, SOURCE_GRAPH_HASH_ALGORITHM, verified.production_model_hash, verified.report_model_hash, payload, existing, True)
        except (OSError, json.JSONDecodeError, TypeError) as exc: raise CanonicalSnapshotStorageError("Existing analysis snapshot is unreadable") from exc
        raise CanonicalSnapshotConflictError("Existing immutable analysis snapshot conflicts")
    payload = {"manifest_version":MANIFEST_VERSION,"verification_policy_version":VERIFICATION_POLICY_VERSION,"path_scope":PATH_SCOPE,"customer_id":customer_id,"project_id":project_id,"procurement_case_id":procurement_case_id,"run_id":run_id,"registry_number":registry_number,"source_analysis_run_id":source_analysis_run_id,"source_graph_hash":verified.source_graph_hash,"source_graph_hash_algorithm":SOURCE_GRAPH_HASH_ALGORITHM,"production_model_hash":verified.production_model_hash,"report_model_hash":verified.report_model_hash,"requirements_relative_path":req_rel,"requirements_file_sha256":verified.requirements_file_sha256,"canonical_report_relative_path":report_rel,"canonical_report_file_sha256":verified.canonical_report_file_sha256,"exact_file_set":EXACT_FILE_SET,"created_at":(created_at or datetime.now(UTC)).isoformat()}
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    temp = Path(tempfile.mkdtemp(prefix=".analysis.partial.", dir=run_root))
    try:
        for name, value in (("requirements.json", verified.requirements_bytes), ("canonical_report.json", verified.canonical_report_bytes), (manifest_name, data)):
            with (temp/name).open("wb") as handle: handle.write(value); handle.flush(); os.fsync(handle.fileno())
        os.replace(temp, final)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True); raise
    return PublishedCanonicalSnapshot(final, final/"requirements.json", final/"canonical_report.json", final/manifest_name, req_rel, report_rel, manifest_rel, verified.requirements_file_sha256, verified.canonical_report_file_sha256, hashlib.sha256(data).hexdigest(), verified.source_graph_hash, SOURCE_GRAPH_HASH_ALGORITHM, verified.production_model_hash, verified.report_model_hash, payload, data, False)
