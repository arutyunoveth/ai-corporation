"""Fast contract tests for the executable R8 tampering matrix."""

from scripts.acceptance.run_r8_tampering import REGISTRY, scenario_pass


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
        "control_customer_unchanged": True,
        "restoration_passed": True,
    }


def test_registry_is_exactly_32_unique_scenarios():
    assert len(REGISTRY) == 32
    assert len({item[0] for item in REGISTRY}) == 32


def test_protected_http_success_rejects_scenario():
    result = _result()
    result["download_http_status"] = 200
    assert not scenario_pass(result)


def test_pdf_disclosure_auto_repair_control_and_restoration_reject_pass():
    for field in ("no_pdf_bytes_returned", "control_customer_unchanged", "restoration_passed"):
        result = _result()
        result[field] = False
        assert not scenario_pass(result)


def test_artifact_layer_requires_artifact_verifier_rejection():
    result = _result("filesystem artifact")
    result["direct_artifact_verifier"] = "UNEXPECTED_PASS"
    assert not scenario_pass(result)
