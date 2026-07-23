"""Fast contract tests for the executable R8 tampering matrix."""

from scripts.acceptance.run_r8_tampering import REGISTRY, branch_head_sha, scenario_pass


def _result(layer="filesystem canonical"):
    return {
        "layer": layer,
        "direct_canonical_verifier": "RunSnapshotBindingConflictError",
        "direct_artifact_verifier": "HTTPException",
        "download_http_status": 409,
        "review_http_status": 409,
        "client_ready_http_status": 409,
        "delivered_http_status": 409,
        "no_500": True,
        "no_pdf_bytes_returned": True,
        "no_foreign_data": True,
        "no_auto_repair": True,
        "no_unrelated_db_mutation": True,
        "control_customer_unchanged": True,
        "control_filesystem_unchanged": True,
        "control_download_passed": True,
        "review_creation_blocked_by_trust_boundary": True,
        "restoration_passed": True,
        "post_restore_canonical_verifier_pass": True,
        "post_restore_artifact_verifier_pass": True,
        "post_restore_pdf_sha256_pass": True,
        "audit_evidence_complete": True,
        "subchecks_complete": True,
        "target_fs_pristine": {"x": {}},
        "target_fs_after_tampering": {"x": {}},
        "target_fs_after_failed_operations": {"x": {}},
        "target_fs_after_restoration": {"x": {}},
        "control_fs_before": {"x": {}},
        "control_fs_after": {"x": {}},
        "target_db_before": {"x": {}},
        "target_db_after_failed_operations": {"x": {}},
    }


def test_registry_is_exactly_32_unique_scenarios():
    assert len(REGISTRY) == 32
    assert len({item[0] for item in REGISTRY}) == 32


def test_protected_http_success_rejects_scenario():
    result = _result()
    result["download_http_status"] = 200
    assert not scenario_pass(result)


def test_each_mandatory_contract_flag_rejects_pass():
    for field in ("no_pdf_bytes_returned", "no_auto_repair", "no_unrelated_db_mutation",
                  "no_foreign_data", "control_customer_unchanged", "control_filesystem_unchanged",
                  "control_download_passed", "review_creation_blocked_by_trust_boundary",
                  "audit_evidence_complete", "subchecks_complete", "restoration_passed",
                  "post_restore_pdf_sha256_pass"):
        result = _result()
        result[field] = False
        assert not scenario_pass(result)


def test_artifact_layer_requires_artifact_verifier_rejection():
    result = _result("filesystem artifact")
    result["direct_artifact_verifier"] = "UNEXPECTED_PASS"
    assert not scenario_pass(result)


def test_empty_snapshots_reject_pass():
    result = _result()
    result["target_fs_pristine"] = {}
    assert not scenario_pass(result)


def test_github_head_sha_is_authoritative(monkeypatch):
    monkeypatch.setenv("GITHUB_HEAD_SHA", "branch-head")
    assert branch_head_sha() == "branch-head"
