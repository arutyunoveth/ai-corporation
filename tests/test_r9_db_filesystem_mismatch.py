"""Runtime contract for the read-only R9 DB/filesystem mismatch characterization."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/acceptance/run_r9_db_filesystem_mismatch.py"
CLASSIFICATIONS = {
    "db_only_canonical_binding", "filesystem_only_canonical_snapshot",
    "incomplete_canonical_snapshot", "canonical_metadata_mismatch",
    "db_only_artifact_generation", "filesystem_only_artifact_generation",
    "incomplete_artifact_generation", "artifact_metadata_mismatch",
}
FILES = {"mismatch-result.json", "canonical-scenarios.json", "artifact-scenarios.json", "database-snapshots.json", "filesystem-snapshots.json", "audit-snapshots.json", "requests.json", "assertions.json", "cleanup.json", "commands.log", "SHA256SUMS"}


def test_db_filesystem_mismatch_runtime_isolated_and_fail_closed() -> None:
    completed = subprocess.run([sys.executable, str(RUNNER)], cwd=ROOT, text=True, capture_output=True, check=True, timeout=120)
    evidence = Path(completed.stdout.strip().splitlines()[-1])
    result = json.loads((evidence / "mismatch-result.json").read_text())
    scenarios = json.loads((evidence / "canonical-scenarios.json").read_text()) + json.loads((evidence / "artifact-scenarios.json").read_text())
    assert {path.name for path in evidence.iterdir()} == FILES
    assert result["scenario_count"] == 8
    assert {item["classification"] for item in scenarios} == CLASSIFICATIONS
    assert result["status"].endswith("FAIL_CLOSED")
    assert result["automatic_repair_performed"] is False
    assert result["filesystem_ownership_imported"] is False
    assert result["orphan_deleted"] is False
    assert result["hygiene"] == {"passed": True, "hits": []}
    assert result["checksum_validator"]["valid"] is True
    assert result["checksum_validator"]["entry_count"] == 10
    assert result["cleanup"]["cleanup_complete"] is True
    assert all(item["database"]["before"] and item["database"]["after"] for item in scenarios)
    assert all("mismatch" in item["filesystem"] and "before" in item["audit"] for item in scenarios)
    assert all(not item["files_overwritten"] and not item["files_deleted"] for item in scenarios)
    assert len({item["database"]["before"]["binding"]["run_id"] for item in scenarios}) == 8
    assert any(item["outcome"] == "unsafe" for item in scenarios)
    assert result["assertions"]["no_filesystem_ownership_import"] is False
