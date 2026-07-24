"""Runtime contract for R9 DB/filesystem mismatch hardening."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/acceptance/run_r9_db_filesystem_mismatch.py"
CLASSIFICATIONS = {
    "db_only_canonical_binding",
    "filesystem_only_canonical_snapshot",
    "incomplete_canonical_snapshot",
    "canonical_metadata_mismatch",
    "db_only_artifact_generation",
    "filesystem_only_artifact_generation",
    "incomplete_artifact_generation",
    "artifact_metadata_mismatch",
}
FILES = {
    "mismatch-result.json",
    "canonical-scenarios.json",
    "artifact-scenarios.json",
    "database-snapshots.json",
    "filesystem-snapshots.json",
    "audit-snapshots.json",
    "requests.json",
    "assertions.json",
    "cleanup.json",
    "commands.log",
    "SHA256SUMS",
}


def test_db_filesystem_mismatch_runtime_isolated_and_fail_closed() -> None:
    completed = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        timeout=240,
    )
    evidence = Path(completed.stdout.strip().splitlines()[-1])
    result = json.loads((evidence / "mismatch-result.json").read_text())
    scenarios = json.loads((evidence / "canonical-scenarios.json").read_text())
    scenarios += json.loads((evidence / "artifact-scenarios.json").read_text())
    by_name = {item["classification"]: item for item in scenarios}

    assert {path.name for path in evidence.iterdir()} == FILES
    assert result["status"] == "R9_5B_DB_FILESYSTEM_MISMATCH_FAIL_CLOSED"
    assert result["scenario_count"] == 8
    assert result["safe_count"] == 8
    assert result["unsafe_count"] == 0
    assert result["inconclusive_count"] == 0
    assert set(by_name) == CLASSIFICATIONS
    assert result["automatic_repair_performed"] is False
    assert result["filesystem_ownership_imported"] is False
    assert result["filesystem_ownership_import_scenarios"] == []
    assert result["orphan_deleted"] is False
    assert result["orphan_deletion_scenarios"] == []
    assert result["tenant_mixing_detected"] is False
    assert result["sentinel_unchanged"] is True
    assert result["hygiene"] == {"passed": True, "hits": []}
    assert result["checksum_validator"]["valid"] is True
    assert result["checksum_validator"]["entry_count"] == 10
    assert result["cleanup"]["cleanup_complete"] is True
    assert all(result["assertions"].values())

    assert all(item["safe"] and item["outcome"] == "safe" for item in scenarios)
    assert all(item["request"]["status_code"] == 409 for item in scenarios)
    assert all(item["retry_request"]["status_code"] == 409 for item in scenarios)
    assert all(item["ownership_unchanged"] for item in scenarios)
    assert all(not item["new_db_row"] for item in scenarios)
    assert all(not item["files_created"] for item in scenarios)
    assert all(not item["files_overwritten"] for item in scenarios)
    assert all(not item["files_deleted"] for item in scenarios)
    assert all(not item["retry_files_created"] for item in scenarios)
    assert all(not item["retry_files_overwritten"] for item in scenarios)
    assert all(not item["retry_files_deleted"] for item in scenarios)

    canonical_orphan = by_name["filesystem_only_canonical_snapshot"]
    assert canonical_orphan["database"]["mismatch"]["binding"] is None
    assert canonical_orphan["database"]["after"]["binding"] is None
    assert canonical_orphan["database"]["after_retry"]["binding"] is None
    assert canonical_orphan["filesystem"]["mismatch"] == canonical_orphan["filesystem"]["after"]
    assert canonical_orphan["filesystem"]["after"] == canonical_orphan["filesystem"]["after_retry"]

    artifact_orphan = by_name["filesystem_only_artifact_generation"]
    assert artifact_orphan["database"]["mismatch"]["artifact"] is None
    assert artifact_orphan["database"]["after"]["artifact"] is None
    assert artifact_orphan["database"]["after_retry"]["artifact"] is None
    assert artifact_orphan["filesystem"]["mismatch"] == artifact_orphan["filesystem"]["after"]
    assert artifact_orphan["filesystem"]["after"] == artifact_orphan["filesystem"]["after_retry"]

    rows = (evidence / "SHA256SUMS").read_text().splitlines()
    assert len(rows) == 10
    assert all("  " in row for row in rows)
    assert "SHA256SUMS" not in {row.split("  ", 1)[1] for row in rows}
