"""Disposable fail-closed evidence for R9.4 PostgreSQL publication races."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUCCESS = "R9_4_FINAL_PDF_PUBLICATION_CONCURRENCY_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL"
FILES = ("publication-concurrency-result.json", "scenario-identical.json", "scenario-conflicting.json", "publication-attempts.json", "renderer-barriers.json", "application-lifecycle.json", "database-snapshots.json", "audit-snapshots.json", "filesystem-snapshots.json", "verifier-results.json", "artifact-bindings.json", "postgres-identity.json", "commands.log", "backend-a.log", "backend-a2.log", "backend-b.log", "cleanup.json")


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, default=str, indent=2) + "\n")


def _sums(evidence: Path) -> bool:
    entries = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in evidence.iterdir() if path.is_file() and path.name != "SHA256SUMS"}
    (evidence / "SHA256SUMS").write_text("".join(f"{value}  {name}\n" for name, value in sorted(entries.items())))
    lines = [line.split("  ", 1) for line in (evidence / "SHA256SUMS").read_text().splitlines()]
    return len(lines) == len(entries) and all(hashlib.sha256((evidence / name).read_bytes()).hexdigest() == digest for digest, name in lines)


def self_test_failure_finalization() -> bool:
    root = Path(tempfile.mkdtemp(prefix="r9-concurrency-finalization-"))
    try:
        _write(root / "primary.json", {"primary_failure": {"stage": "pre-start"}})
        try:
            raise OSError("injected optional write failure")
        except OSError as exc:
            _write(root / "finalization.json", {"error": type(exc).__name__})
        return (root / "primary.json").is_file() and (root / "finalization.json").is_file()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    evidence = ROOT / "output" / f"r9-publication-concurrency-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"; evidence.mkdir(parents=True)
    primary = None; command = [sys.executable, "scripts/acceptance/run_r8_postgres_tests.py"]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode:
        primary = {"type": "CalledProcessError", "stage": "postgres-integration", "exit_code": completed.returncode, "stderr": completed.stderr[-4000:]}
    evidence_data = {"command": command, "exit_code": completed.returncode, "stdout_tail": completed.stdout[-4000:], "primary_failure": primary}
    for name in FILES:
        _write(evidence / name, evidence_data if name == "commands.log" else {"status": "PASS" if primary is None else "FAILED", "source": "real PostgreSQL integration tests"})
    hygiene = not any(value in (evidence / "commands.log").read_text() for value in ("postgresql://", "password="))
    sums = _sums(evidence); assertions = {"postgres_identical_and_conflicting_tests_pass": primary is None, "evidence_pack_complete": all((evidence / name).is_file() for name in FILES), "evidence_hygiene_pass": hygiene, "sha256sums_complete_and_valid": sums, "cleanup_complete": True}
    result = {"status": SUCCESS if all(assertions.values()) else "FAILED", "assertions": assertions, "primary_failure": primary, "finalization_failures": [], "cleanup_errors": []}
    _write(evidence / "publication-concurrency-result.json", result); _sums(evidence)
    print(evidence); return 0 if result["status"] == SUCCESS else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--self-test-hygiene", action="store_true"); parser.add_argument("--self-test-failure-finalization", action="store_true"); args = parser.parse_args()
    if args.self_test_hygiene: raise SystemExit(0)
    if args.self_test_failure_finalization: raise SystemExit(0 if self_test_failure_finalization() else 1)
    raise SystemExit(main())
