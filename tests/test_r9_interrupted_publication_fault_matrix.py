from __future__ import annotations

import hashlib
import argparse
import json
import tempfile
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modules.customer_pilot import canonical_snapshot
from src.modules.customer_pilot.artifact_snapshot import (
    FinalPdfArtifactConflictError,
    FinalPdfArtifactStorageError,
    derive_final_pdf_artifact_identity,
    publish_final_pdf_generation,
)
from src.modules.customer_pilot.canonical_snapshot import (
    CanonicalSnapshotStorageError,
    publish_canonical_snapshot,
)
from src.modules.procurement_analysis.frozen_producer import (
    produce_frozen_canonical_analysis,
)


CANONICAL_PRE = (
    "after_temp_created",
    "after_requirements_written",
    "after_canonical_written",
    "after_manifest_written",
    "before_temp_directory_fsync",
    "before_rename",
)
CANONICAL_POST = ("after_rename", "before_parent_fsync")
ARTIFACT_PRE = (
    "after_pdf_written",
    "after_manifest_written",
    "before_temp_directory_fsync",
    "before_rename",
)
ARTIFACT_POST = ("after_rename", "before_parent_fsync")


def _config(root: Path):
    return lambda: type("Config", (), {"data_dir": str(root)})()


def _canonical(root: Path):
    produced = produce_frozen_canonical_analysis(
        registry_number="0379100000726000101",
        run_id="11111111-1111-1111-1111-111111111111",
        output_dir=root / "working",
        metadata={},
        documents=[],
        source_analysis_run_id="22222222-2222-2222-2222-222222222222",
    )
    kwargs = dict(
        customer_id="CUST-R9",
        project_id="11111111-1111-1111-1111-111111111111",
        procurement_case_id="33333333-3333-3333-3333-333333333333",
        run_id="44444444-4444-4444-4444-444444444444",
        registry_number="0379100000726000101",
        source_analysis_run_id=produced.source_analysis_run_id,
        verified=produced.persisted,
        now_factory=lambda: datetime(2026, 7, 24, tzinfo=UTC),
    )
    return kwargs


def _artifact() -> dict[str, object]:
    digest = "a" * 64
    identity = derive_final_pdf_artifact_identity(
        registry_number="0379100000726000101",
        run_id="run-r9",
        report_model_hash=digest,
        customer_id="CUST-R9",
        project_id="project-r9",
        procurement_case_id="case-r9",
    )
    return dict(
        customer_id="CUST-R9",
        project_id="project-r9",
        procurement_case_id="case-r9",
        run_id="run-r9",
        run_result_id="result-r9",
        registry_number="0379100000726000101",
        source_analysis_run_id="source-r9",
        run_namespace_key="namespace-r9",
        artifact_key=identity.artifact_key,
        renderer_version="r7-persisted-pdf-v2",
        requirements_storage_key="customer-pilot/CUST-R9/project-r9/case-r9/run-r9/analysis/requirements.json",
        requirements_file_sha256=digest,
        canonical_report_storage_key="customer-pilot/CUST-R9/project-r9/case-r9/run-r9/analysis/canonical_report.json",
        canonical_report_file_sha256=digest,
        binding_manifest_storage_key="customer-pilot/CUST-R9/project-r9/case-r9/run-r9/analysis/canonical-binding.manifest.json",
        binding_manifest_file_sha256=digest,
        source_graph_hash=digest,
        source_graph_hash_algorithm="sha256-json-c14n-v1",
        production_model_hash=digest,
        report_model_hash=digest,
        pdf_bytes=b"%PDF-1.4\nR9-A\n%%EOF\n",
        now_factory=lambda: datetime(2026, 7, 24, tzinfo=UTC),
    )


def _fault(point: str):
    def callback(observed: str) -> None:
        if observed == point:
            raise OSError(f"r9-fault-{point}")

    return callback


@pytest.mark.parametrize("point", CANONICAL_PRE + CANONICAL_POST)
def test_canonical_fault_matrix_preserves_or_recovers_immutable_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, point: str
) -> None:
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    kwargs = _canonical(tmp_path)
    with pytest.raises(CanonicalSnapshotStorageError):
        publish_canonical_snapshot(**kwargs, fault=_fault(point))
    root = tmp_path / "customer-pilot" / "CUST-R9" / kwargs["project_id"] / kwargs["procurement_case_id"] / kwargs["run_id"]
    final = root / "analysis"
    partials = list(root.glob(".analysis.partial.*"))
    if point in CANONICAL_PRE:
        assert not final.exists()
        # The callback sits immediately after mkdtemp; a process-style abort
        # leaves this server-shaped partial for the next publisher to reap.
        if point == "after_temp_created":
            assert len(partials) == 1
        else:
            assert partials == []
        first = publish_canonical_snapshot(**kwargs)
        assert not first.idempotent
        assert list(root.glob(".analysis.partial.*")) == []
    else:
        assert final.is_dir()
        assert partials == []
        before = {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in final.iterdir()}
        first = publish_canonical_snapshot(**kwargs)
        assert first.idempotent
        assert before == {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in final.iterdir()}
    assert sorted(p.name for p in final.iterdir()) == ["canonical-binding.manifest.json", "canonical_report.json", "requirements.json"]
    assert publish_canonical_snapshot(**kwargs).idempotent


@pytest.mark.parametrize("point", ARTIFACT_PRE + ARTIFACT_POST)
def test_artifact_fault_matrix_preserves_or_recovers_immutable_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, point: str
) -> None:
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    kwargs = _artifact()
    with pytest.raises(FinalPdfArtifactStorageError):
        publish_final_pdf_generation(**kwargs, fault=_fault(point))
    artifacts = tmp_path / "customer-pilot" / "CUST-R9" / "project-r9" / "case-r9" / "run-r9" / "artifacts"
    final = artifacts / str(kwargs["artifact_key"])
    partials = list(artifacts.glob(".artifact.*.partial.*")) if artifacts.exists() else []
    if point in ARTIFACT_PRE:
        assert not final.exists()
        assert partials == []
        first = publish_final_pdf_generation(**kwargs, allow_existing_verified=False)
        assert not first.idempotent
    else:
        assert final.is_dir()
        assert partials == []
        before = {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in final.iterdir()}
        first = publish_final_pdf_generation(**kwargs, allow_existing_verified=False)
        assert first.idempotent
        assert before == {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns) for p in final.iterdir()}
        with pytest.raises(FinalPdfArtifactConflictError):
            publish_final_pdf_generation(
                **{**kwargs, "pdf_bytes": b"%PDF-1.4\nR9-B\n%%EOF\n"},
                allow_existing_verified=False,
            )
    assert sorted(p.name for p in final.iterdir()) == ["artifact.manifest.json", "final.pdf"]


def _file_state(directory: Path) -> tuple[dict[str, str], dict[str, int]]:
    return (
        {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()},
        {p.name: p.stat().st_mtime_ns for p in directory.iterdir()},
    )


def _canonical_report(point: str) -> dict[str, object]:
    root = Path(tempfile.mkdtemp(prefix="r9-matrix-canonical-")).resolve()
    original = canonical_snapshot.load_config
    try:
        canonical_snapshot.load_config = _config(root)
        kwargs = _canonical(root)
        try:
            publish_canonical_snapshot(**kwargs, fault=_fault(point))
        except CanonicalSnapshotStorageError as exc:
            exception_type = type(exc).__name__
        else:
            raise AssertionError("fault did not fire")
        run = root / "customer-pilot" / "CUST-R9" / kwargs["project_id"] / kwargs["procurement_case_id"] / kwargs["run_id"]
        final = run / "analysis"; partials = sorted(run.glob(".analysis.partial.*"))
        before_h, before_m = _file_state(final) if final.exists() else ({}, {})
        partial_entries = sorted(p.name for item in partials for p in item.iterdir())
        retried = publish_canonical_snapshot(**kwargs)
        after_h, after_m = _file_state(final)
        return {"fault_point":point,"phase":"post_rename" if point in CANONICAL_POST else "pre_rename","exception_type":exception_type,"final_exists_after_fault":final.exists() if point in CANONICAL_POST else False,"partial_count_after_fault":len(partials),"partial_names":[p.name for p in partials],"partial_entries":partial_entries,"retry_success":True,"retry_idempotent":retried.idempotent,"final_entries":sorted(p.name for p in final.iterdir()),"hashes_before_retry":before_h,"hashes_after_retry":after_h,"mtimes_before_retry":before_m,"mtimes_after_retry":after_m,"bytes_unchanged":before_h==after_h and before_m==after_m if point in CANONICAL_POST else True}
    finally:
        canonical_snapshot.load_config = original; shutil.rmtree(root, ignore_errors=True)


def _artifact_report(point: str) -> dict[str, object]:
    root = Path(tempfile.mkdtemp(prefix="r9-matrix-artifact-")).resolve(); original = canonical_snapshot.load_config
    try:
        canonical_snapshot.load_config = _config(root); kwargs = _artifact()
        try: publish_final_pdf_generation(**kwargs, fault=_fault(point))
        except FinalPdfArtifactStorageError as exc: exception_type = type(exc).__name__
        else: raise AssertionError("fault did not fire")
        artifacts=root/"customer-pilot"/"CUST-R9"/"project-r9"/"case-r9"/"run-r9"/"artifacts"; final=artifacts/str(kwargs["artifact_key"]); partials=sorted(artifacts.glob(".artifact.*.partial.*")) if artifacts.exists() else []
        before_h,before_m=_file_state(final) if final.exists() else ({},{})
        partial_entries=sorted(p.name for item in partials for p in item.iterdir())
        retried=publish_final_pdf_generation(**kwargs,allow_existing_verified=False); after_h,after_m=_file_state(final)
        conflict=False
        if point in ARTIFACT_POST:
            with pytest.raises(FinalPdfArtifactConflictError): publish_final_pdf_generation(**{**kwargs,"pdf_bytes":b"%PDF-1.4\nR9-B\n%%EOF\n"},allow_existing_verified=False)
            conflict=True
        return {"fault_point":point,"phase":"post_rename" if point in ARTIFACT_POST else "pre_rename","exception_type":exception_type,"final_exists_after_fault":bool(before_h),"partial_count_after_fault":len(partials),"partial_names":[p.name for p in partials],"partial_entries":partial_entries,"same_bytes_retry_success":True,"same_bytes_idempotent":retried.idempotent,"conflicting_retry_rejected":conflict,"final_entries":sorted(p.name for p in final.iterdir()),"hashes_before_retry":before_h,"hashes_after_retry":after_h,"mtimes_before_retry":before_m,"mtimes_after_retry":after_m,"bytes_unchanged":before_h==after_h and before_m==after_m if point in ARTIFACT_POST else True}
    finally:
        canonical_snapshot.load_config=original; shutil.rmtree(root,ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--json-report", type=Path, required=True); args = parser.parse_args()
    report = {"canonical":[_canonical_report(point) for point in CANONICAL_PRE + CANONICAL_POST],"artifact":[_artifact_report(point) for point in ARTIFACT_PRE + ARTIFACT_POST]}
    args.json_report.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
