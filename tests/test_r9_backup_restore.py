"""Acceptance contract for R9 backup and restore hardening."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/acceptance/run_r9_backup_restore.py"
FILES = {
    "backup-restore-result.json",
    "backup-manifest.json",
    "consistent-restore.json",
    "db-only-mismatch.json",
    "filesystem-only-mismatch.json",
    "cross-tenant-mismatch.json",
    "snapshots.json",
    "assertions.json",
    "cleanup.json",
    "commands.log",
    "SHA256SUMS",
}


def test_backup_restore_matrix_is_consistent_and_fail_closed() -> None:
    completed = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        timeout=420,
    )
    evidence = Path(completed.stdout.strip().splitlines()[-1])
    result = json.loads((evidence / "backup-restore-result.json").read_text())
    manifest = json.loads((evidence / "backup-manifest.json").read_text())
    consistent = json.loads((evidence / "consistent-restore.json").read_text())
    db_only = json.loads((evidence / "db-only-mismatch.json").read_text())
    fs_only = json.loads((evidence / "filesystem-only-mismatch.json").read_text())
    cross = json.loads((evidence / "cross-tenant-mismatch.json").read_text())

    assert {path.name for path in evidence.iterdir()} == FILES
    assert result["status"] == "R9_P2_BACKUP_RESTORE_FAIL_CLOSED"
    assert result["backup_created"] is True
    assert result["consistent_restore"] is True
    assert result["db_only_mismatch_fail_closed"] is True
    assert result["filesystem_only_mismatch_fail_closed"] is True
    assert result["cross_tenant_mismatch_rejected"] is True
    assert all(result["assertions"].values())
    assert result["cleanup"]["cleanup_complete"] is True
    assert result["hygiene"] == {"passed": True, "hits": []}
    assert result["checksum_validator"]["valid"] is True

    assert manifest["format_version"] == "r9-recovery-v1"
    assert manifest["quiesced"] is True
    assert manifest["tenant_scope"] == ["R9-RECOVERY"]
    assert manifest["exact_file_set"] == ["database.dump", "filesystem.tar", "manifest.json"]

    assert consistent["safe"] is True
    assert consistent["receipt"]["database_restored"] is True
    assert consistent["receipt"]["filesystem_restored"] is True
    assert consistent["download"]["status_code"] == 200

    assert db_only["safe"] is True
    assert db_only["download"]["status_code"] == 409
    assert db_only["database"]["artifact"] is not None
    assert db_only["filesystem"]["files"] == []

    assert fs_only["safe"] is True
    assert fs_only["case_request"]["status_code"] == 404
    assert fs_only["database"]["binding"] is None
    assert fs_only["database"]["artifact"] is None
    assert fs_only["filesystem"]["files"]

    assert cross["safe"] is True
    assert cross["rejected"] is True
    assert cross["database"]["table_count"] == 0
    assert cross["filesystem"]["exists"] is False

    rows = (evidence / "SHA256SUMS").read_text().splitlines()
    assert len(rows) == 10
    assert "SHA256SUMS" not in {line.split("  ", 1)[1] for line in rows}
