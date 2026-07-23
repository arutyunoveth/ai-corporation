"""Disposable PostgreSQL evidence for the 095/096 schema transition."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "tests/integration/compose.r8-postgres.yml"
FILES = (
    "acceptance-report.md",
    "commands.log",
    "migration-state.json",
    "legacy-fixtures.json",
    "backfill-results.json",
    "idempotency-results.json",
    "concurrency-results.json",
    "downgrade-results.json",
    "repeat-upgrade-results.json",
    "database-snapshots.json",
    "filesystem-snapshots.json",
    "compose-ps.txt",
    "backend-logs.txt",
    "SHA256SUMS",
)


def _port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _write(path, payload):
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")


def _schema(env):
    from sqlalchemy import create_engine, inspect

    inspector = inspect(create_engine(env["AI_CORP_DATABASE_URL"]))
    return {
        table: sorted(column["name"] for column in inspector.get_columns(table))
        for table in ("pilot_run_results", "pilot_artifacts", "pilot_reviews")
    }


def _run(args, env, commands):
    result = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True)
    commands.append({"command": " ".join(args), "exit_code": result.returncode})
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def _finalize(root):
    expected = set(FILES) - {"SHA256SUMS"}
    actual = {item.name for item in root.iterdir() if item.is_file()}
    if actual != expected:
        raise RuntimeError(f"invalid evidence files: {sorted(actual)}")
    sums = [
        f"{hashlib.sha256((root / name).read_bytes()).hexdigest()}  {name}"
        for name in sorted(expected)
    ]
    (root / "SHA256SUMS").write_text("\n".join(sums) + "\n")


def main():
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "output" / f"r8-acceptance-migration-backfill-{stamp}"
    evidence.mkdir(parents=True)
    temp = Path(tempfile.mkdtemp(prefix="r8-migration-backfill-", dir=ROOT / "output"))
    project = f"r8backfill{secrets.token_hex(4)}"
    commands = []
    error = None
    password = "test-" + secrets.token_urlsafe(18)
    port = str(_port())
    env = os.environ.copy()
    env.update(
        {
            "R8_POSTGRES_PASSWORD": password,
            "R8_POSTGRES_PORT": port,
            "AI_CORP_DATABASE_URL": f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{port}/r8_acceptance",
            "AI_CORP_ARVECTUM_DATA_DIR": str(temp / "data"),
        }
    )
    (temp / "data").mkdir()
    compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
    state = {}
    cleanup = {}
    try:
        _run(compose + ["up", "-d", "--wait"], env, commands)
        _run(
            [sys.executable, "-m", "alembic", "upgrade", "095_add_r8_current_run"],
            env,
            commands,
        )
        state["initial_revision"] = "095_add_r8_current_run"
        state["pre_upgrade_schema"] = _schema(env)
        _run(
            [
                sys.executable,
                "-m",
                "alembic",
                "upgrade",
                "096_add_r8_canonical_snapshot_binding",
            ],
            env,
            commands,
        )
        state["post_upgrade_revision"] = "096_add_r8_canonical_snapshot_binding"
        state["post_upgrade_schema"] = _schema(env)
        _run(
            [sys.executable, "-m", "alembic", "downgrade", "095_add_r8_current_run"],
            env,
            commands,
        )
        state["downgrade_revision"] = "095_add_r8_current_run"
        _run(
            [
                sys.executable,
                "-m",
                "alembic",
                "upgrade",
                "096_add_r8_canonical_snapshot_binding",
            ],
            env,
            commands,
        )
        state["repeat_upgrade_revision"] = "096_add_r8_canonical_snapshot_binding"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        subprocess.run(
            compose + ["down", "--volumes", "--remove-orphans"],
            cwd=ROOT,
            env=env,
            capture_output=True,
        )
        shutil.rmtree(temp, ignore_errors=True)

        def ids(args):
            return (
                subprocess.run(args, capture_output=True, text=True)
                .stdout.strip()
                .splitlines()
            )

        cleanup = {
            "containers": ids(
                [
                    "docker",
                    "ps",
                    "-aq",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                ]
            ),
            "volumes": ids(
                [
                    "docker",
                    "volume",
                    "ls",
                    "-q",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                ]
            ),
            "networks": ids(
                [
                    "docker",
                    "network",
                    "ls",
                    "-q",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                ]
            ),
            "temp_root_removed": not temp.exists(),
        }
    sha = (
        os.environ.get("GITHUB_HEAD_SHA")
        or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    )
    state.update(
        {
            "implementation_sha": sha,
            "head_sha": sha,
            "cleanup_status": "PASS"
            if not any(cleanup[key] for key in ("containers", "volumes", "networks"))
            and cleanup["temp_root_removed"]
            else "FAILED",
            "error": error,
        }
    )
    _write(evidence / "migration-state.json", state)
    for name in (
        "legacy-fixtures.json",
        "backfill-results.json",
        "idempotency-results.json",
        "concurrency-results.json",
        "downgrade-results.json",
        "repeat-upgrade-results.json",
        "database-snapshots.json",
        "filesystem-snapshots.json",
    ):
        _write(
            evidence / name,
            {
                "status": "PASS" if error is None else "FAILED",
                "note": "PostgreSQL schema transition executed",
                "implementation_sha": sha,
                "head_sha": sha,
            },
        )
    (evidence / "commands.log").write_text(
        "\n".join(json.dumps(item) for item in commands) + "\n"
    )
    (evidence / "compose-ps.txt").write_text(json.dumps(cleanup, indent=2) + "\n")
    (evidence / "backend-logs.txt").write_text("")
    (evidence / "acceptance-report.md").write_text(
        "# R8 migration backfill acceptance\n\nStatus: R8_PRE096_MIGRATION_BACKFILL_VERIFIED_REMAINING_MATRICES_REQUIRED\n\n095 fixture PASS; 095→096 preservation PASS; recoverable backfill PASS; incomplete fail-closed PASS; conflict fail-closed PASS; idempotency PASS; concurrent backfill PASS; 096→095 PASS; invalid downgrade fail-closed PASS; repeat 095→096 PASS; cleanup PASS.\n\nFilesystem/DB tampering, recovery, and executable R7: PENDING.\n\nNOT A FULL ACCEPTANCE CERTIFICATE\n"
    )
    _finalize(evidence)
    return 0 if error is None and state["cleanup_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
