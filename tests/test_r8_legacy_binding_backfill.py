from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.modules.customer_pilot.legacy_binding_backfill import (
    backfill_legacy_run_binding,
)
from scripts.acceptance.run_r8_migration_backfill import _fixture as production_fixture


class Session:
    def __init__(self):
        self.flushes = 0

    def flush(self):
        self.flushes += 1


class Result(SimpleNamespace):
    @property
    def is_verified_snapshot_binding(self):
        return all(
            getattr(self, field, None)
            for field in (
                "requirements_storage_key",
                "requirements_file_sha256",
                "canonical_report_file_sha256",
                "binding_manifest_storage_key",
                "binding_manifest_file_sha256",
                "source_graph_hash_algorithm",
                "report_model_hash",
                "verification_policy_version",
            )
        )


def _fixture(tmp_path: Path, monkeypatch, missing=False, conflict=False):
    ids = production_fixture(tmp_path, "RECOVERABLE", 1)
    run = SimpleNamespace(
        customer_id=ids["customer_id"],
        project_id=ids["project_id"],
        id=ids["run_id"],
        registry_number="0379100000726000101",
        artifact_key=ids["run_namespace_key"],
    )
    case = SimpleNamespace(
        customer_id=ids["customer_id"], project_id=ids["project_id"], id=ids["case_id"]
    )
    result = Result(
        id=ids["run_result_id"],
        customer_id=ids["customer_id"],
        project_id=ids["project_id"],
        procurement_case_id=ids["case_id"],
        run_id=ids["run_id"],
        source_analysis_run_id=ids["source_run_id"],
        canonical_report_storage_key=ids["canonical_report_storage_key"],
        canonical_report_hash="f" * 64 if conflict else ids["legacy_hash"],
        source_graph_hash=ids["source_graph_hash"],
        production_model_hash=ids["production_model_hash"],
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
        id=ids["artifact_id"],
        customer_id=ids["customer_id"],
        project_id=ids["project_id"],
        procurement_case_id=ids["case_id"],
        run_id=ids["run_id"],
        run_result_id=ids["run_result_id"],
        artifact_type="final_pdf",
        artifact_key=ids["artifact_key"],
        report_model_hash=ids["legacy_hash"],
        source_graph_hash=ids["source_graph_hash"],
        renderer_version=ids["renderer_version"],
        manifest_relative_path=ids["manifest_relative_path"],
        pdf_relative_path=ids["pdf_relative_path"],
        pdf_sha256=ids["pdf_sha256"],
        byte_size=ids["byte_size"],
        status="published",
        manifest_file_sha256=None,
        verification_policy_version=None,
    )
    if missing:
        (tmp_path / ids["canonical_report_storage_key"]).with_name(
            "canonical-binding.manifest.json"
        ).unlink()
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
