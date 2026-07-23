from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.modules.customer_pilot import canonical_snapshot
from src.modules.customer_pilot.legacy_binding_backfill import (
    backfill_legacy_run_binding,
)
from src.modules.procurement_analysis.frozen_producer import (
    produce_frozen_canonical_analysis,
)


class Session:
    def __init__(self):
        self.flushes = 0

    def flush(self):
        self.flushes += 1


def _config(root):
    return lambda: type("Config", (), {"data_dir": str(root)})()


def _fixture(tmp_path: Path, monkeypatch, missing=False, conflict=False):
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    ids = {
        "customer_id": "CUST",
        "project_id": "11111111-1111-1111-1111-111111111111",
        "case_id": "22222222-2222-2222-2222-222222222222",
        "run_id": "33333333-3333-3333-3333-333333333333",
        "result_id": "44444444-4444-4444-4444-444444444444",
    }
    produced = produce_frozen_canonical_analysis(
        registry_number="0379100000726000101",
        run_id=ids["run_id"],
        output_dir=tmp_path / "work",
        metadata={},
        documents=[],
        source_analysis_run_id="55555555-5555-5555-5555-555555555555",
    )
    published = canonical_snapshot.publish_canonical_snapshot(
        customer_id=ids["customer_id"],
        project_id=ids["project_id"],
        procurement_case_id=ids["case_id"],
        run_id=ids["run_id"],
        registry_number="0379100000726000101",
        source_analysis_run_id=produced.source_analysis_run_id,
        verified=produced.persisted,
    )
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    (artifact_dir / "final.pdf").write_bytes(b"%PDF-1.4\n")
    (artifact_dir / "artifact.manifest.json").write_text("{}\n")
    run = SimpleNamespace(
        customer_id=ids["customer_id"],
        project_id=ids["project_id"],
        id=ids["run_id"],
        registry_number="0379100000726000101",
    )
    case = SimpleNamespace(
        customer_id=ids["customer_id"], project_id=ids["project_id"], id=ids["case_id"]
    )
    result = SimpleNamespace(
        id=ids["result_id"],
        customer_id=ids["customer_id"],
        project_id=ids["project_id"],
        procurement_case_id=ids["case_id"],
        run_id=ids["run_id"],
        source_analysis_run_id=produced.source_analysis_run_id,
        canonical_report_storage_key=published.canonical_report_relative_path,
        canonical_report_hash="bad"
        if conflict
        else produced.persisted.report_model_hash,
        source_graph_hash=produced.persisted.source_graph_hash,
        production_model_hash=produced.persisted.production_model_hash,
        requirements_storage_key=None,
        requirements_file_sha256=None,
        canonical_report_file_sha256=None,
        binding_manifest_storage_key=None,
        binding_manifest_file_sha256=None,
        source_graph_hash_algorithm=None,
        report_model_hash=None,
        verification_policy_version=None,
    )
    artifact = SimpleNamespace(
        customer_id=ids["customer_id"],
        project_id=ids["project_id"],
        procurement_case_id=ids["case_id"],
        run_id=ids["run_id"],
        run_result_id=ids["result_id"],
        manifest_relative_path="artifact",
        manifest_file_sha256=None,
        verification_policy_version=None,
    )
    if missing:
        (published.analysis_directory / "canonical-binding.manifest.json").unlink()
    return Session(), run, case, result, artifact


def test_valid_legacy_bundle_backfills_then_is_idempotent(tmp_path, monkeypatch):
    session, run, case, result, artifact = _fixture(tmp_path, monkeypatch)
    assert (
        backfill_legacy_run_binding(
            session=session,
            run=run,
            case=case,
            run_result=result,
            artifact=artifact,
            data_root=tmp_path,
        ).status
        == "BACKFILLED"
    )
    assert (
        result.report_model_hash
        and artifact.manifest_file_sha256
        and artifact.verification_policy_version
    )
    result.is_verified_snapshot_binding = True
    assert (
        backfill_legacy_run_binding(
            session=session,
            run=run,
            case=case,
            run_result=result,
            artifact=artifact,
            data_root=tmp_path,
        ).status
        == "ALREADY_VERIFIED"
    )


def test_missing_manifest_is_fail_closed_without_writes(tmp_path, monkeypatch):
    session, run, case, result, artifact = _fixture(tmp_path, monkeypatch, missing=True)
    assert (
        backfill_legacy_run_binding(
            session=session,
            run=run,
            case=case,
            run_result=result,
            artifact=artifact,
            data_root=tmp_path,
        ).status
        == "INCOMPLETE"
    )
    assert (
        result.report_model_hash is None
        and artifact.manifest_file_sha256 is None
        and session.flushes == 0
    )


def test_conflicting_legacy_hash_is_fail_closed_without_writes(tmp_path, monkeypatch):
    session, run, case, result, artifact = _fixture(
        tmp_path, monkeypatch, conflict=True
    )
    assert (
        backfill_legacy_run_binding(
            session=session,
            run=run,
            case=case,
            run_result=result,
            artifact=artifact,
            data_root=tmp_path,
        ).status
        == "CONFLICT"
    )
    assert (
        result.report_model_hash is None
        and artifact.manifest_file_sha256 is None
        and session.flushes == 0
    )
