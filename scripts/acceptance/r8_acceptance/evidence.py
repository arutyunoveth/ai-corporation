from __future__ import annotations

import hashlib
import json
import os
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


class EvidenceContext:
    __slots__ = ("implementation_sha", "checked_out_sha", "branch_head_sha", "workflow_context")

    def __init__(self, implementation_sha: str, checked_out_sha: str, branch_head_sha: str, workflow_context: dict):
        self.implementation_sha = implementation_sha
        self.checked_out_sha = checked_out_sha
        self.branch_head_sha = branch_head_sha
        self.workflow_context = workflow_context

    @classmethod
    def from_environment(cls, root: Path) -> "EvidenceContext":
        checked_out = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
        github_sha = os.environ.get("GITHUB_SHA", "")
        branch_head = os.environ.get("GITHUB_HEAD_SHA") or checked_out
        mode = "github_actions" if os.environ.get("GITHUB_ACTIONS") else "local"
        if mode == "github_actions" and github_sha != branch_head and not os.environ.get("GITHUB_HEAD_SHA"):
            raise ValueError("synthetic GitHub merge SHA cannot be used as branch head")
        return cls(checked_out, checked_out, branch_head, {"mode": mode, "workflow_run_id": os.environ.get("GITHUB_RUN_ID", "local"), "workflow_name": os.environ.get("GITHUB_WORKFLOW", "local"), "job_name": os.environ.get("GITHUB_JOB", "local"), "ref": os.environ.get("GITHUB_REF", "local"), "event_name": os.environ.get("GITHUB_EVENT_NAME", "local")})


class ScenarioRegistry:
    def __init__(self, required: tuple[str, ...]):
        if not required or len(set(required)) != len(required):
            raise ValueError("scenario registry must be non-empty and unique")
        self.required = required


def validate_matrix_result(*, registry: ScenarioRegistry, results: dict[str, str], checks: list[dict], cleanup_status: str, context: EvidenceContext, errors: list[str]) -> None:
    if not checks or cleanup_status != "PASS" or errors:
        raise ValueError("matrix PASS requires checks, cleanup PASS, and no errors")
    if not context.implementation_sha or not context.branch_head_sha or context.branch_head_sha == "UNKNOWN":
        raise ValueError("matrix PASS requires known Git metadata")
    if set(results) != set(registry.required) or any(value != "PASS" for value in results.values()):
        raise ValueError("matrix scenarios do not exactly satisfy the required registry")


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
    required_scenarios: tuple[str, ...] | None = None,
    scenario_results: dict[str, str] | None = None,
) -> dict:
    errors = errors or []
    if status == "PASS":
        try:
            registry = ScenarioRegistry(required_scenarios or ())
            results = scenario_results or {}
            context = EvidenceContext(implementation_sha or "", implementation_sha or "", head_sha or "", workflow_context or {})
            validate_matrix_result(registry=registry, results=results, checks=checks, cleanup_status=cleanup_status, context=context, errors=errors)
            scenario_count, passed_count = len(registry.required), len(results)
            failed_count = pending_count = 0
        except ValueError as exc:
            status = "FAILED_EVIDENCE_CONTRACT"
            errors = [*errors, str(exc)]
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
