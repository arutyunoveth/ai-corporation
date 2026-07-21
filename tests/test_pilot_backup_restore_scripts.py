from __future__ import annotations

import json
import hashlib
import os
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESTORE = ROOT / "deploy/pilot/scripts/restore.sh"
BACKUP = ROOT / "deploy/pilot/scripts/backup.sh"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(script), *args], text=True, capture_output=True, cwd=ROOT)


def _valid_restore_package(tmp_path: Path, pdf_path: str) -> tuple[Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    backup = tmp_path / "valid-backup"; backup.mkdir()
    env = tmp_path / "env"; env.write_text("AI_CORP_PILOT_AUTH_USERNAME=u\nAI_CORP_PILOT_AUTH_PASSWORD=p\n")
    trust = tmp_path / "trust"; trust.mkdir()
    pdf = b"%PDF-1.4\nfixture\n"
    with tarfile.open(backup / "artifacts.tar.gz", "w:gz") as archive:
        payload = tmp_path / "fixture.pdf"; payload.write_bytes(pdf)
        archive.add(payload, arcname="data/demo/exports/demo_agent_report_abc123.pdf")
    (backup / "database.dump").write_bytes(b"dump")
    manifest = {"manifest_version": 1, "source_project": "source", "accepted_run": {"run_id": "toa-run-valid-001", "pdf_relative_path": pdf_path, "pdf_sha256": hashlib.sha256(pdf).hexdigest(), "byte_size": len(pdf)}, "alembic": {"repository_head": "abc", "database_head": "abc", "matched": True}}
    (backup / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    checks = "".join(f"{hashlib.sha256((backup / name).read_bytes()).hexdigest()}  {name}\n" for name in ("database.dump", "artifacts.tar.gz", "manifest.json"))
    (backup / "SHA256SUMS").write_text(checks)
    return backup, env, trust


def test_restore_rejects_malicious_pdf_paths_before_docker(tmp_path: Path) -> None:
    malicious = ["../../etc/passwd", "/absolute/report.pdf", "data/demo/exports/a.pdf;id", "data/demo/exports/$(id).pdf", "data/demo/exports/a b.pdf", "data/demo/exports/a//b.pdf", "data\\demo\\exports\\a.pdf", "data/demo/other/a.pdf", "data/demo/exports/subdir/a.pdf"]
    for path in malicious:
        backup, env, trust = _valid_restore_package(tmp_path / hashlib.sha1(path.encode()).hexdigest(), path)
        result = _run(RESTORE, "--backup", str(backup), "--target-project", "target", "--env-file", str(env), "--compose-file", str(ROOT / "deploy/pilot/compose.yaml"), "--trust-dir", str(trust), "--port", "18082")
        assert result.returncode != 0
        assert "unsafe accepted PDF path" in result.stderr


def test_restore_accepts_valid_pdf_path_past_manifest_validation(tmp_path: Path) -> None:
    backup, env, trust = _valid_restore_package(tmp_path, "data/demo/exports/demo_agent_report_abc123.pdf")
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8")); manifest["source_project"] = "target"
    (backup / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    checks = "".join(f"{hashlib.sha256((backup / name).read_bytes()).hexdigest()}  {name}\n" for name in ("database.dump", "artifacts.tar.gz", "manifest.json"))
    (backup / "SHA256SUMS").write_text(checks)
    result = _run(RESTORE, "--backup", str(backup), "--target-project", "target", "--env-file", str(env), "--compose-file", str(ROOT / "deploy/pilot/compose.yaml"), "--trust-dir", str(trust), "--port", "18082")
    assert "unsafe accepted PDF path" not in result.stderr
    assert "target must differ" in result.stderr


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
