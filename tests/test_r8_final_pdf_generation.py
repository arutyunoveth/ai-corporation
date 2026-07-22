from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

from src.modules.customer_pilot import canonical_snapshot
from src.modules.customer_pilot.artifact_snapshot import (
    FinalPdfArtifactError,
    FinalPdfArtifactConflictError,
    FinalPdfArtifactContractError,
    publish_final_pdf_generation,
    verify_final_pdf_generation,
)


def _config(root):
    return lambda: type("Config", (), {"data_dir": str(root)})()


def _kwargs():
    digest = "a" * 64
    return {
        "customer_id": "CUST-A",
        "project_id": "project_a",
        "procurement_case_id": "case_a",
        "run_id": "run_a",
        "run_result_id": "result_a",
        "registry_number": "0379100000726000101",
        "source_analysis_run_id": "source_a",
        "run_namespace_key": "namespace_a",
        "artifact_key": hashlib.sha256(
            b"0379100000726000101\0run_a\0" + b"a" * 64 + b"\0r7-persisted-pdf-v2"
        ).hexdigest()[:24],
        "renderer_version": "r7-persisted-pdf-v2",
        "requirements_storage_key": "customer-pilot/CUST-A/project_a/case_a/run_a/analysis/requirements.json",
        "requirements_file_sha256": digest,
        "canonical_report_storage_key": "customer-pilot/CUST-A/project_a/case_a/run_a/analysis/canonical_report.json",
        "canonical_report_file_sha256": digest,
        "binding_manifest_storage_key": "customer-pilot/CUST-A/project_a/case_a/run_a/analysis/canonical-binding.manifest.json",
        "binding_manifest_file_sha256": digest,
        "source_graph_hash": digest,
        "source_graph_hash_algorithm": "sha256-json-c14n-v1",
        "production_model_hash": digest,
        "report_model_hash": digest,
        "pdf_bytes": b"%PDF-1.4\ntrusted pdf\n",
    }


def test_atomic_final_pdf_generation_is_idempotent_and_exact(tmp_path, monkeypatch):
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    first = publish_final_pdf_generation(
        **_kwargs(), now_factory=lambda: datetime(2026, 7, 22, tzinfo=UTC)
    )
    before = first.pdf_path.stat().st_mtime_ns
    second = publish_final_pdf_generation(**_kwargs())
    assert not first.idempotent and second.idempotent
    assert second.pdf_path.read_bytes() == _kwargs()["pdf_bytes"]
    assert second.pdf_path.stat().st_mtime_ns == before
    assert (
        second.manifest_file_sha256 == hashlib.sha256(second.manifest_bytes).hexdigest()
    )


def test_final_pdf_generation_rejects_conflict_and_tampering(tmp_path, monkeypatch):
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    generated = publish_final_pdf_generation(**_kwargs())
    changed = {**_kwargs(), "pdf_bytes": b"%PDF-1.4\nother\n"}
    with pytest.raises(FinalPdfArtifactConflictError):
        publish_final_pdf_generation(**changed, allow_existing_verified=False)
    generated.pdf_path.write_bytes(b"%PDF-1.4\ntampered\n")
    expected = {
        key: generated.manifest[key]
        for key in generated.manifest
        if key
        not in {
            "manifest_version",
            "verification_policy_version",
            "path_scope",
            "exact_file_set",
            "created_at",
        }
    }
    with pytest.raises(FinalPdfArtifactContractError):
        verify_final_pdf_generation(
            customer_id="CUST-A",
            project_id="project_a",
            procurement_case_id="case_a",
            run_id="run_a",
            expected=expected,
        )


def test_final_pdf_generation_recovers_after_post_rename_fault(tmp_path, monkeypatch):
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))

    def fault(point):
        if point == "after_rename":
            raise OSError("injected")

    with pytest.raises(FinalPdfArtifactError):
        publish_final_pdf_generation(**_kwargs(), fault=fault)
    # The immutable generation was renamed; retry verifies it without overwrite.
    assert publish_final_pdf_generation(**_kwargs()).idempotent


@pytest.mark.parametrize("tamper", ("manifest", "extra_file", "symlink"))
def test_final_pdf_generation_fails_closed_for_unsafe_existing_tree(
    tmp_path, monkeypatch, tamper
):
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    generated = publish_final_pdf_generation(**_kwargs())
    if tamper == "manifest":
        generated.manifest_path.write_bytes(b"{}")
    elif tamper == "extra_file":
        (generated.artifact_directory / "foreign.txt").write_text("foreign")
    else:
        generated.pdf_path.unlink()
        generated.pdf_path.symlink_to(tmp_path / "outside.pdf")
    with pytest.raises(FinalPdfArtifactError):
        publish_final_pdf_generation(**_kwargs())
