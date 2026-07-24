"""Focused security checks for the R9 recovery command."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
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


def _valid_backup_with_archive(root: Path) -> Path:
    root.mkdir()
    database = root / "database.dump"
    filesystem = root / "filesystem.tar"
    database.write_bytes(b"database")
    with tarfile.open(filesystem, "w") as archive:
        payload = b"immutable"
        info = tarfile.TarInfo("data/customer-pilot/customer-a/file.txt")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    manifest = {
        "format_version": r9_recovery.FORMAT_VERSION,
        "backup_id": "r9-20260724T000000Z-12345678",
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


def test_restore_requires_explicit_expected_tenant_scope(tmp_path) -> None:
    with pytest.raises(r9_recovery.RecoveryError, match="Expected tenant scope"):
        r9_recovery.restore_backup(
            database_url="postgresql://invalid/unused",
            data_dir=tmp_path / "data",
            backup_dir=tmp_path / "missing-backup",
            expected_tenants=None,
            quiesced=True,
        )


def test_external_tool_failure_does_not_echo_stderr_or_credentials(monkeypatch) -> None:
    secret = "postgresql://operator:super-secret@example.invalid/database"

    def failed(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["pg_restore"],
            returncode=9,
            stdout="",
            stderr=f"connection failed for {secret}",
        )

    monkeypatch.setattr(r9_recovery.subprocess, "run", failed)
    with pytest.raises(r9_recovery.RecoveryError) as captured:
        r9_recovery._run(["pg_restore", secret], {})
    message = str(captured.value)
    assert message == "pg_restore failed with exit code 9"
    assert "super-secret" not in message
    assert secret not in message


def test_restore_rolls_back_installed_filesystem_when_database_restore_fails(
    monkeypatch, tmp_path
) -> None:
    backup = _valid_backup_with_archive(tmp_path / "backup")
    data_dir = tmp_path / "restored-data"
    data_dir.mkdir()
    monkeypatch.setattr(r9_recovery, "_database_is_empty", lambda _url: True)

    observed = {"filesystem_visible_during_database_restore": False}

    def failed_restore_database(*, database_url: str, database_dump: Path) -> None:
        assert database_url == "postgresql://ignored/target"
        assert database_dump == backup / "database.dump"
        observed["filesystem_visible_during_database_restore"] = (
            data_dir / "customer-pilot/customer-a/file.txt"
        ).read_bytes() == b"immutable"
        raise r9_recovery.RecoveryError("injected database restore failure")

    monkeypatch.setattr(r9_recovery, "restore_database", failed_restore_database)
    with pytest.raises(r9_recovery.RecoveryError, match="injected database restore failure"):
        r9_recovery.restore_backup(
            database_url="postgresql://ignored/target",
            data_dir=data_dir,
            backup_dir=backup,
            expected_tenants={"customer-a"},
            quiesced=True,
        )

    assert observed["filesystem_visible_during_database_restore"] is True
    assert data_dir.is_dir()
    assert list(data_dir.iterdir()) == []
    assert not list(tmp_path.glob(".restored-data.restore.*"))
    assert not list(tmp_path.glob(".r9-restore-*.json"))
