from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESTORE = ROOT / "deploy/pilot/scripts/restore.sh"
BACKUP = ROOT / "deploy/pilot/scripts/backup.sh"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(script), *args], text=True, capture_output=True, cwd=ROOT)


def _backup(tmp_path: Path, source: str = "source") -> Path:
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "database.dump").write_bytes(b"dump")
    (backup / "artifacts.tar.gz").write_bytes(b"not-a-tar")
    (backup / "manifest.json").write_text(json.dumps({"manifest_version": 1, "source_project": source}), encoding="utf-8")
    (backup / "SHA256SUMS").write_text("bad  database.dump\n", encoding="utf-8")
    return backup


def test_backup_requires_explicit_trust_dir(tmp_path: Path) -> None:
    result = _run(BACKUP, "--output", str(tmp_path / "out"), "--project-name", "pilot", "--env-file", str(tmp_path / "env"), "--compose-file", str(tmp_path / "compose"))
    assert result.returncode != 0


def test_restore_rejects_staging_before_docker(tmp_path: Path) -> None:
    result = _run(RESTORE, "--backup", str(tmp_path), "--target-project", "arvectum-r7-staging", "--env-file", "x", "--compose-file", "x", "--trust-dir", "x", "--port", "18082")
    assert result.returncode != 0
    assert "forbidden" in result.stderr


def test_restore_rejects_invalid_target_and_port_before_docker(tmp_path: Path) -> None:
    args = ("--backup", str(tmp_path), "--env-file", "x", "--compose-file", "x", "--trust-dir", "x")
    assert _run(RESTORE, *args, "--target-project", ".*", "--port", "18082").returncode != 0
    assert _run(RESTORE, *args, "--target-project", "valid", "--port", "18081").returncode != 0


def test_restore_rejects_checksum_mismatch_without_mutating_package(tmp_path: Path) -> None:
    backup = _backup(tmp_path)
    before = {item.name: item.read_bytes() for item in backup.iterdir()}
    result = _run(RESTORE, "--backup", str(backup), "--target-project", "target", "--env-file", "x", "--compose-file", "x", "--trust-dir", "x", "--port", "18082")
    assert result.returncode != 0
    assert before == {item.name: item.read_bytes() for item in backup.iterdir()}


def test_restore_rejects_source_project_before_docker(tmp_path: Path) -> None:
    backup = _backup(tmp_path, "same")
    # A valid checksum is not needed: checksum validation is intentionally first.
    result = _run(RESTORE, "--backup", str(backup), "--target-project", "same", "--env-file", "x", "--compose-file", "x", "--trust-dir", "x", "--port", "18082")
    assert result.returncode != 0
