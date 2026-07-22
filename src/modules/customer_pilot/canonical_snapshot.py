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

@dataclass(frozen=True)
class PublishedCanonicalSnapshot:
    analysis_directory: Path; requirements_path: Path; canonical_report_path: Path; binding_manifest_path: Path
    requirements_relative_path: str; canonical_report_relative_path: str; binding_manifest_relative_path: str
    requirements_file_sha256: str; canonical_report_file_sha256: str; binding_manifest_file_sha256: str
    source_graph_hash: str; source_graph_hash_algorithm: str; production_model_hash: str; report_model_hash: str
    manifest: dict; manifest_bytes: bytes; idempotent: bool

def _root(*values: str) -> Path:
    if any(not _SAFE.fullmatch(value) for value in values): raise ValueError("Unsafe customer snapshot segment")
    root = Path(load_config().data_dir).resolve()
    path = root.joinpath("customer-pilot", *values)
    for parent in [root, *[root.joinpath("customer-pilot", *values[:i]) for i in range(0, len(values) + 1)]]:
        if parent.exists() and (parent.is_symlink() or not parent.is_dir()): raise RuntimeError("Unsafe customer snapshot directory")
    return path

def publish_canonical_snapshot(*, customer_id: str, project_id: str, procurement_case_id: str, run_id: str, registry_number: str, source_analysis_run_id: str | None, verified: PersistedCanonicalOutputs, created_at: datetime | None = None) -> PublishedCanonicalSnapshot:
    run_root = _root(customer_id, project_id, procurement_case_id, run_id); run_root.mkdir(parents=True, exist_ok=True)
    final = run_root / "analysis"; manifest_name = "canonical-binding.manifest.json"
    req_rel, report_rel, manifest_rel = "analysis/requirements.json", "analysis/canonical_report.json", f"analysis/{manifest_name}"
    if final.exists():
        if final.is_symlink() or not final.is_dir(): raise RuntimeError("Existing analysis snapshot is unsafe")
        try:
            existing = (final / manifest_name).read_bytes(); payload = json.loads(existing)
            expected = {"customer_id":customer_id,"project_id":project_id,"procurement_case_id":procurement_case_id,"run_id":run_id,"registry_number":registry_number,"source_analysis_run_id":source_analysis_run_id,"source_graph_hash":verified.source_graph_hash,"source_graph_hash_algorithm":SOURCE_GRAPH_HASH_ALGORITHM,"production_model_hash":verified.production_model_hash,"report_model_hash":verified.report_model_hash,"requirements_file_sha256":verified.requirements_file_sha256,"canonical_report_file_sha256":verified.canonical_report_file_sha256}
            if (final / "requirements.json").read_bytes() == verified.requirements_bytes and (final / "canonical_report.json").read_bytes() == verified.canonical_report_bytes and all(payload.get(k) == v for k, v in expected.items()):
                return PublishedCanonicalSnapshot(final, final/"requirements.json", final/"canonical_report.json", final/manifest_name, req_rel, report_rel, manifest_rel, verified.requirements_file_sha256, verified.canonical_report_file_sha256, hashlib.sha256(existing).hexdigest(), verified.source_graph_hash, SOURCE_GRAPH_HASH_ALGORITHM, verified.production_model_hash, verified.report_model_hash, payload, existing, True)
        except OSError as exc: raise RuntimeError("Existing analysis snapshot is unreadable") from exc
        raise RuntimeError("Existing immutable analysis snapshot conflicts")
    payload = {"manifest_version":"r8-canonical-binding-v1","verification_policy_version":"r8-frozen-canonical-verifier-v1","path_scope":"data-root-relative","customer_id":customer_id,"project_id":project_id,"procurement_case_id":procurement_case_id,"run_id":run_id,"registry_number":registry_number,"source_analysis_run_id":source_analysis_run_id,"source_graph_hash":verified.source_graph_hash,"source_graph_hash_algorithm":SOURCE_GRAPH_HASH_ALGORITHM,"production_model_hash":verified.production_model_hash,"report_model_hash":verified.report_model_hash,"requirements_relative_path":str(Path("customer-pilot")/customer_id/project_id/procurement_case_id/run_id/req_rel),"requirements_file_sha256":verified.requirements_file_sha256,"canonical_report_relative_path":str(Path("customer-pilot")/customer_id/project_id/procurement_case_id/run_id/report_rel),"canonical_report_file_sha256":verified.canonical_report_file_sha256,"exact_file_set":["requirements.json","canonical_report.json",manifest_name],"created_at":(created_at or datetime.now(UTC)).isoformat()}
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    temp = Path(tempfile.mkdtemp(prefix=".analysis.partial.", dir=run_root))
    try:
        for name, value in (("requirements.json", verified.requirements_bytes), ("canonical_report.json", verified.canonical_report_bytes), (manifest_name, data)):
            with (temp/name).open("wb") as handle: handle.write(value); handle.flush(); os.fsync(handle.fileno())
        os.replace(temp, final)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True); raise
    return PublishedCanonicalSnapshot(final, final/"requirements.json", final/"canonical_report.json", final/manifest_name, req_rel, report_rel, manifest_rel, verified.requirements_file_sha256, verified.canonical_report_file_sha256, hashlib.sha256(data).hexdigest(), verified.source_graph_hash, SOURCE_GRAPH_HASH_ALGORITHM, verified.production_model_hash, verified.report_model_hash, payload, data, False)
