"""Acceptance contract for R9 orphan and lifecycle hardening."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/acceptance/run_r9_orphan_lifecycle.py"
CLASSIFICATIONS = {
    "filesystem_only_canonical_orphan",
    "filesystem_only_artifact_orphan",
    "approved_review_without_artifact",
    "needs_reanalysis_blocks_client_ready",
    "tampered_artifact_blocks_client_ready",
    "stale_review_blocks_client_ready",
    "delivered_requires_client_ready",
    "verified_happy_path",
}
FILES = {
    "orphan-lifecycle-result.json",
    "orphan-scenarios.json",
    "lifecycle-scenarios.json",
    "database-snapshots.json",
    "filesystem-snapshots.json",
    "requests.json",
    "assertions.json",
    "cleanup.json",
    "commands.log",
    "SHA256SUMS",
}


def test_orphan_and_lifecycle_matrix_is_fail_closed() -> None:
    completed = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        timeout=300,
    )
    evidence = Path(completed.stdout.strip().splitlines()[-1])
    result = json.loads((evidence / "orphan-lifecycle-result.json").read_text())
    scenarios = json.loads((evidence / "orphan-scenarios.json").read_text())
    scenarios += json.loads((evidence / "lifecycle-scenarios.json").read_text())
    by_name = {item["classification"]: item for item in scenarios}

    assert {path.name for path in evidence.iterdir()} == FILES
    assert result["status"] == "R9_5C_ORPHAN_AND_LIFECYCLE_FAIL_CLOSED"
    assert result["scenario_count"] == 8
    assert result["safe_count"] == 8
    assert result["unsafe_count"] == 0
    assert set(by_name) == CLASSIFICATIONS
    assert all(result["assertions"].values())
    assert result["orphan_imported"] is False
    assert result["orphan_deleted"] is False
    assert result["lifecycle_advanced_without_verified_review"] is False
    assert result["cleanup"]["cleanup_complete"] is True
    assert result["hygiene"] == {"passed": True, "hits": []}
    assert result["checksum_validator"]["valid"] is True
    assert all(item["safe"] for item in scenarios)

    canonical = by_name["filesystem_only_canonical_orphan"]
    assert [item["status_code"] for item in canonical["requests"]] == [409, 409]
    assert canonical["database"]["after"]["binding"] is None
    assert canonical["details"]["orphan_preserved"] is True

    artifact = by_name["filesystem_only_artifact_orphan"]
    assert [item["status_code"] for item in artifact["requests"]] == [409, 409]
    assert artifact["database"]["after"]["artifact"] is None
    assert artifact["details"]["orphan_preserved"] is True

    assert by_name["approved_review_without_artifact"]["requests"][0]["status_code"] == 409
    assert by_name["needs_reanalysis_blocks_client_ready"]["database"]["after"]["case"]["status"] == "operator_review"
    assert by_name["tampered_artifact_blocks_client_ready"]["requests"][-1]["status_code"] == 409
    assert by_name["stale_review_blocks_client_ready"]["database"]["after"]["case"]["status"] == "analyzing"
    assert by_name["delivered_requires_client_ready"]["database"]["after"]["case"]["status"] == "operator_review"
    assert by_name["verified_happy_path"]["database"]["after"]["case"]["status"] == "delivered"

    rows = (evidence / "SHA256SUMS").read_text().splitlines()
    assert len(rows) == 9
    assert "SHA256SUMS" not in {line.split("  ", 1)[1] for line in rows}
