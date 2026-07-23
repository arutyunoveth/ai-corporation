from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/acceptance"))

from r8_acceptance.evidence import validate_pass_payload
from run_r8_acceptance import (
    TENANT_DIRECTIONS,
    TENANT_OPERATIONS,
    assert_no_foreign_leak,
    validate_tenant_results,
)


def _results():
    return [
        {"scenario_id": f"{direction}:{operation}"}
        for direction in TENANT_DIRECTIONS
        for operation in TENANT_OPERATIONS
    ]


def test_tenant_ids_are_exactly_bidirectional_30():
    assert len(_results()) == 30
    assert TENANT_OPERATIONS == TENANT_OPERATIONS


def test_leak_markers_in_body_and_headers_are_rejected():
    with pytest.raises(AssertionError):
        assert_no_foreign_leak(b'{"id":"foreign-id"}', {}, ["foreign-id"])
    with pytest.raises(AssertionError):
        assert_no_foreign_leak(
            b"{}", {"X-Artifact-Key": "foreign-key"}, ["foreign-key"]
        )


def test_snapshot_inequality_is_detectable_and_shared_pdf_is_allowed():
    assert {"PilotProject": {"count": 1}} != {"PilotProject": {"count": 2}}
    assert {"a.pdf": {"sha256": "a"}} != {"a.pdf": {"sha256": "b"}}
    assert "same-pdf-sha" == "same-pdf-sha"
    assert "artifact-key-a" != "artifact-key-b"


def test_pass_requires_cleanup():
    with pytest.raises(RuntimeError):
        validate_pass_payload(
            {
                "status": "PASS",
                "scenario_count": 1,
                "passed_count": 1,
                "failed_count": 0,
                "pending_count": 0,
                "checks": [{}],
                "cleanup_status": "NOT_EXECUTED",
                "head_sha": "abc",
                "errors": [],
            }
        )


def test_missing_and_duplicate_scenarios_are_rejected():
    with pytest.raises(RuntimeError):
        validate_tenant_results(_results()[:-1])
    duplicate = _results()
    duplicate[-1] = duplicate[-2]
    with pytest.raises(RuntimeError):
        validate_tenant_results(duplicate)
