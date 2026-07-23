"""Unit coverage for the reusable, non-production acceptance evidence helpers."""

from __future__ import annotations

import importlib.util
import socket
from pathlib import Path


MODULE = (
    Path(__file__).parents[1]
    / "scripts"
    / "acceptance"
    / "r8_acceptance"
    / "evidence.py"
)
SPEC = importlib.util.spec_from_file_location("r8_acceptance_evidence", MODULE)
assert SPEC and SPEC.loader
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)
RUNTIME = (
    Path(__file__).parents[1]
    / "scripts"
    / "acceptance"
    / "r8_acceptance"
    / "runtime.py"
)
RUNTIME_SPEC = importlib.util.spec_from_file_location("r8_acceptance_runtime", RUNTIME)
assert RUNTIME_SPEC and RUNTIME_SPEC.loader
runtime = importlib.util.module_from_spec(RUNTIME_SPEC)
RUNTIME_SPEC.loader.exec_module(runtime)


def test_foundation_evidence_has_exact_fourteen_files_and_verifiable_sums(
    tmp_path: Path,
) -> None:
    for name in evidence.EVIDENCE_FILES:
        if name != "SHA256SUMS":
            (tmp_path / name).write_text(name + "\n", encoding="utf-8")
    evidence.finalize(tmp_path)
    names = [
        line.split("  ", 1)[1]
        for line in (tmp_path / "SHA256SUMS").read_text().splitlines()
    ]
    assert names == sorted(set(evidence.EVIDENCE_FILES) - {"SHA256SUMS"})
    assert {item.name for item in tmp_path.iterdir()} == set(evidence.EVIDENCE_FILES)


def test_sanitizer_removes_auth_database_password_cookie_and_temp_path(
    tmp_path: Path,
) -> None:
    raw = (
        f"Authorization: Basic dXNlcjpwYXNz\n"
        "postgresql+psycopg://user:password@host/database "
        "PILOT_AUTH_PASSWORD=s3cr3t Cookie: session=private "
        f"{tmp_path}/private"
    )
    safe = evidence.sanitize(raw, tmp_path)
    for secret in (
        "dXNlcjpwYXNz",
        "password",
        "s3cr3t",
        "session=private",
        str(tmp_path),
    ):
        assert secret not in safe
    assert "<REDACTED>" in safe
    assert "<TEMP_ROOT>" in safe


def test_pending_matrix_is_not_pass() -> None:
    payload = evidence.matrix(
        status="PENDING_NOT_EXECUTED", started_at=evidence.utcnow(), checks=[]
    )
    assert payload["status"] != "PASS"
    assert payload["phase"] == "foundation"


def test_compose_names_are_unique_and_dynamic_ports_are_bindable() -> None:
    assert runtime.compose_project_name().startswith("r8acceptance")
    assert runtime.compose_project_name() != runtime.compose_project_name()
    port = runtime.free_port()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
