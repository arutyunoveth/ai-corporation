from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path


EVIDENCE_FILES = (
    "acceptance-report.md",
    "commands.log",
    "migration-state.json",
    "lifecycle-results.json",
    "tenant-isolation-results.json",
    "concurrency-results.json",
    "restart-results.json",
    "tampering-results.json",
    "recovery-results.json",
    "artifact-inventory.json",
    "database-counts.json",
    "backend-logs.txt",
    "compose-ps.txt",
    "SHA256SUMS",
)


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def sanitize(value: str, temp_root: Path | None = None) -> str:
    value = re.sub(r"(?i)(authorization:\s*basic\s+)[^\s]+", r"\1<REDACTED>", value)
    value = re.sub(r"(?i)(cookie:\s*)\S+", r"\1<REDACTED>", value)
    value = re.sub(r"(?i)(password|token|secret)=([^\s&]+)", r"\1=<REDACTED>", value)
    value = re.sub(
        r"(postgresql(?:\+psycopg)?://[^:/\s]+:)[^@/\s]+@", r"\1<REDACTED>@", value
    )
    if temp_root:
        value = value.replace(str(temp_root), "<TEMP_ROOT>")
    return value


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def matrix(
    *,
    phase: str = "foundation",
    status: str,
    started_at: str,
    checks: list[dict],
    actual: dict | None = None,
    errors: list[str] | None = None,
    head_sha: str | None = None,
    cleanup_status: str = "NOT_EXECUTED",
    scenario_count: int = 0,
    passed_count: int = 0,
    failed_count: int = 0,
    pending_count: int = 0,
    implementation_sha: str | None = None,
    workflow_context: dict | None = None,
) -> dict:
    implementation_sha = implementation_sha or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    head_sha = head_sha or implementation_sha
    valid_pass = (
        status == "PASS"
        and scenario_count > 0
        and passed_count == scenario_count
        and failed_count == pending_count == 0
        and bool(checks)
        and cleanup_status == "PASS"
        and head_sha != "UNKNOWN"
    )
    if status == "PASS" and not valid_pass:
        status = "FAILED_EVIDENCE_CONTRACT"
        errors = [*(errors or []), "PASS matrix metadata contract is incomplete"]
    return {
        "schema_version": "r8-acceptance-evidence-v1",
        "phase": phase,
        "status": status,
        "started_at": started_at,
        "finished_at": utcnow(),
        "checks": checks,
        "expected": {},
        "actual": actual or {},
        "errors": errors or [],
        "implementation_sha": implementation_sha,
        "head_sha": head_sha,
        "workflow_context": workflow_context or {},
        "cleanup_status": cleanup_status,
        "scenario_count": scenario_count,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "pending_count": pending_count,
    }


def validate_pass_payload(payload: dict) -> None:
    """Reject incomplete PASS evidence before it is persisted."""
    if not (
        payload.get("status") == "PASS"
        and payload.get("scenario_count", 0) > 0
        and payload.get("passed_count") == payload.get("scenario_count")
        and payload.get("failed_count") == 0
        and payload.get("pending_count") == 0
        and bool(payload.get("checks"))
        and payload.get("cleanup_status") == "PASS"
        and payload.get("head_sha") not in (None, "", "UNKNOWN")
        and not payload.get("errors")
    ):
        raise RuntimeError("PASS evidence payload contract is incomplete")


def finalize(root: Path) -> None:
    expected = set(EVIDENCE_FILES) - {"SHA256SUMS"}
    actual = {item.name for item in root.iterdir() if item.is_file()}
    if actual != expected:
        raise RuntimeError(f"evidence file set is invalid: {sorted(actual)}")
    lines = []
    for name in sorted(expected):
        lines.append(
            f"{hashlib.sha256((root / name).read_bytes()).hexdigest()}  {name}"
        )
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for line in lines:
        digest, name = line.split("  ", 1)
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError("evidence checksum verification failed")
