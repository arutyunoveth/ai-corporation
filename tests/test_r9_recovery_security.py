"""Focused security checks for the R9 recovery command."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RECOVERY_CLI = ROOT / "scripts/ops/r9_recovery.py"
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
import r9_recovery  # noqa: E402


def _backup(root: Path, *, backup_id: str) -> Path:
    root.mkdir()
    database = root / "database.dump"
    filesystem = root / "filesystem.tar"
    database.write_bytes(b"database")
    filesystem.write_bytes(b"filesystem")
    manifest = {
        "format_version": r9_recovery.FORMAT_VERSION,
        "backup_id": backup_id,
        "created_at": datetime.now(UTC).isoformat(),
        "quiesced": True,
        "exact_file_set": sorted(r9_recovery.BACKUP_FILES),
        "database_sha256": r9_recovery.sha256(database),
        "filesystem_sha256": r9_recovery.sha256(filesystem),
        "database_tenants": ["customer-a"],
        "filesystem_tenants": ["customer-a"],
        "tenant_scope": ["customer-a"],
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    return root


def test_manifest_backup_id_cannot_escape_receipt_directory(tmp_path) -> None:
    backup = _backup(tmp_path / "backup", backup_id="r9-../../outside")
    with pytest.raises(r9_recovery.RecoveryError, match="manifest policy"):
        r9_recovery.verify_backup(backup)


def test_malformed_manifest_cli_is_sanitized(tmp_path) -> None:
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "database.dump").write_bytes(b"database")
    (backup / "filesystem.tar").write_bytes(b"filesystem")
    (backup / "manifest.json").write_text("{not-json")
    completed = subprocess.run(
        [sys.executable, str(RECOVERY_CLI), "verify", "--backup-dir", str(backup)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "Traceback" not in completed.stderr
    assert json.loads(completed.stderr) == {
        "ok": False,
        "error": "Backup manifest is invalid",
    }
