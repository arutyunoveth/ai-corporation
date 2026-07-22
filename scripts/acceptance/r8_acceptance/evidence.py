from __future__ import annotations

import hashlib
import json
import re
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
) -> dict:
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
    }


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
