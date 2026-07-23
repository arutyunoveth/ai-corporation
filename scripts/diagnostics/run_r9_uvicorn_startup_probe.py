#!/usr/bin/env python3
"""One-shot, disposable uvicorn startup diagnostic for R9.0A.

This deliberately proves only process startup.  It is neither an acceptance
runner nor a restart test.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "tests" / "integration" / "compose.r8-postgres.yml"
EXPECTED_REVISION = "096_add_r8_canonical_snapshot_binding"
STARTUP_TIMEOUT_SECONDS = 15


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def redacted_database_target(port: int) -> str:
    return f"postgresql+psycopg://r8_acceptance:***@127.0.0.1:{port}/r8_acceptance"


def run_command(args: list[str], env: dict[str, str], commands: list[dict]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    commands.append(
        {
            "command": " ".join(args),
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    )
    if result.returncode:
        raise RuntimeError(f"command failed: {' '.join(args)} (exit {result.returncode})")
    return result


def http_status(url: str) -> int | None:
    try:
        with urlopen(url, timeout=1) as response:
            return response.status
    except HTTPError as exc:
        return exc.code
    except OSError:
        return None


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256sums(evidence: Path) -> None:
    lines = []
    for path in sorted(evidence.iterdir()):
        if path.name == "SHA256SUMS" or not path.is_file():
            continue
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (evidence / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "output" / f"r9-uvicorn-startup-probe-{stamp}"
    evidence.mkdir(parents=True, exist_ok=False)
    temporary = Path(tempfile.mkdtemp(prefix="r9-uvicorn-probe-", dir=ROOT / "output"))
    data_root = temporary / "data"
    data_root.mkdir(mode=0o700)
    pg_port, api_port = free_port(), free_port()
    pg_password = "r9-" + secrets.token_urlsafe(24)
    project = "r9probe" + secrets.token_hex(5)
    database_url = f"postgresql+psycopg://r8_acceptance:{pg_password}@127.0.0.1:{pg_port}/r8_acceptance"
    env = os.environ.copy()
    env.update(
        {
            "R8_POSTGRES_PASSWORD": pg_password,
            "R8_POSTGRES_PORT": str(pg_port),
            "AI_CORP_DATABASE_URL": database_url,
            "AI_CORP_ARVECTUM_DATA_DIR": str(data_root),
            "AI_CORP_PILOT_AUTH_ENABLED": "false",
            "AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED": "false",
        }
    )
    commands: list[dict] = []
    statuses: dict[str, int | None] = {}
    cleanup: dict[str, object] = {"uvicorn": False, "compose_down": False, "temporary_directory_removed": False}
    result: dict[str, object] = {
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "python": {"executable": sys.executable, "version": sys.version},
        "repository_cwd": str(ROOT),
        "uvicorn_command": [sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", str(api_port)],
        "ports": {"postgres": pg_port, "uvicorn": api_port},
        "startup_timeout_seconds": STARTUP_TIMEOUT_SECONDS,
        "alembic_revision": None,
        "http_statuses": statuses,
        "uvicorn_pid": None,
        "process_return_code": None,
        "startup_result": "FAILED",
        "cleanup_result": cleanup,
        "dotenv_files_present": [name for name in (".env", ".env.local") if (ROOT / name).exists()],
        "relevant_environment_names": sorted(key for key in env if key.startswith("AI_CORP_") or key.startswith("R8_POSTGRES_")),
    }
    server: subprocess.Popen[str] | None = None
    log_handle = None
    compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
    try:
        run_command(compose + ["up", "-d", "--wait"], env, commands)
        run_command([sys.executable, "-m", "alembic", "upgrade", "head"], env, commands)
        revision_probe = (
            "from sqlalchemy import create_engine,text; import os; "
            "e=create_engine(os.environ['AI_CORP_DATABASE_URL']); "
            "print(e.connect().execute(text('select version_num from alembic_version')).scalar_one())"
        )
        revision = run_command([sys.executable, "-c", revision_probe], env, commands).stdout.strip()
        result["alembic_revision"] = revision
        if revision != EXPECTED_REVISION:
            raise RuntimeError(f"unexpected Alembic revision: {revision}")

        configuration_probe = (
            "import json; from sqlalchemy.engine import make_url; "
            "from src.shared.config.settings import get_settings; "
            "from src.shared.db.session import engine; "
            "s=get_settings(); u=make_url(s.database_url); eu=engine.url; "
            "print(json.dumps({'settings_database_target': f'{u.drivername}://{u.host}:{u.port}/{u.database}', "
            "'data_root': s.arvectum_data_dir, 'engine_target': f'{eu.drivername}://{eu.host}:{eu.port}/{eu.database}', "
            "'pilot_auth_enabled': s.pilot_auth_is_enabled()}))"
        )
        config = json.loads(run_command([sys.executable, "-c", configuration_probe], env, commands).stdout)
        expected_target = f"postgresql+psycopg://127.0.0.1:{pg_port}/r8_acceptance"
        if config != {"settings_database_target": expected_target, "data_root": str(data_root), "engine_target": expected_target, "pilot_auth_enabled": False}:
            raise RuntimeError("configuration probe did not match disposable settings")
        write_json(evidence / "effective-settings-redacted.json", config)

        log_handle = (evidence / "backend.log").open("w", encoding="utf-8")
        server = subprocess.Popen(result["uvicorn_command"], cwd=ROOT, env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True)
        result["uvicorn_pid"] = server.pid
        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            return_code = server.poll()
            if return_code is not None:
                result["process_return_code"] = return_code
                raise RuntimeError(f"uvicorn exited before liveness probe (exit {return_code})")
            statuses["health"] = http_status(f"http://127.0.0.1:{api_port}/health")
            if statuses["health"] == 200:
                break
            time.sleep(0.2)
        else:
            raise TimeoutError("uvicorn liveness probe timed out")
        statuses["openapi"] = http_status(f"http://127.0.0.1:{api_port}/openapi.json")
        statuses["health_ready"] = http_status(f"http://127.0.0.1:{api_port}/health/ready")
        result["startup_result"] = "PASS"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if server is not None:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
            result["process_return_code"] = server.returncode
            cleanup["uvicorn"] = True
        if log_handle is not None:
            log_handle.close()
        else:
            (evidence / "backend.log").touch()
        down = subprocess.run(compose + ["down", "-v", "--remove-orphans"], cwd=ROOT, env=env, text=True, capture_output=True, check=False)
        commands.append({"command": " ".join(down.args), "exit_code": down.returncode, "stdout": down.stdout, "stderr": down.stderr})
        cleanup["compose_down"] = down.returncode == 0
        ps = subprocess.run(compose + ["ps"], cwd=ROOT, env=env, text=True, capture_output=True, check=False)
        (evidence / "compose-ps.txt").write_text(ps.stdout + ps.stderr, encoding="utf-8")
        try:
            shutil.rmtree(temporary)
            cleanup["temporary_directory_removed"] = not temporary.exists()
        except OSError as exc:
            cleanup["temporary_directory_error"] = str(exc)
        write_json(evidence / "commands.log", commands)
        write_json(evidence / "cleanup.json", cleanup)
        write_json(evidence / "startup-probe.json", result)
        sha256sums(evidence)
    print(evidence)
    return 0 if result["startup_result"] == "PASS" and all(cleanup.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
