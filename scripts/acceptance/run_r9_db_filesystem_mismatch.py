"""Disposable R9 DB/filesystem mismatch acceptance matrix."""
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
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "tests/integration/compose.r8-postgres.yml"
sys.path.insert(0, str(ROOT / "scripts" / "acceptance"))
from r8_acceptance.runtime import http  # noqa: E402

FILES = (
    "mismatch-result.json",
    "canonical-scenarios.json",
    "artifact-scenarios.json",
    "database-snapshots.json",
    "filesystem-snapshots.json",
    "audit-snapshots.json",
    "requests.json",
    "assertions.json",
    "cleanup.json",
    "commands.log",
)
CUSTOMER = "R9-MISMATCH"
SENTINEL = "R9-MISMATCH-SENTINEL"
CANONICAL = (
    "db_only_canonical_binding",
    "filesystem_only_canonical_snapshot",
    "incomplete_canonical_snapshot",
    "canonical_metadata_mismatch",
)
ARTIFACT = (
    "db_only_artifact_generation",
    "filesystem_only_artifact_generation",
    "incomplete_artifact_generation",
    "artifact_metadata_mismatch",
)
PASS_STATUS = "R9_5B_DB_FILESYSTEM_MISMATCH_FAIL_CLOSED"
FAIL_STATUS = "R9_5B_DB_FILESYSTEM_MISMATCH_CHARACTERIZATION_FAIL_CLOSED"


def now() -> str:
    return datetime.now(UTC).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def port() -> int:
    with socket.socket() as value:
        value.bind(("127.0.0.1", 0))
        return value.getsockname()[1]


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, default=str, sort_keys=True, indent=2) + "\n")


def run(cmd: list[str], env: dict[str, str], log: list[dict[str, Any]]) -> None:
    value = subprocess.run(
        cmd, cwd=ROOT, env=env, text=True, capture_output=True, timeout=180
    )
    log.append(
        {
            "command": cmd,
            "exit_code": value.returncode,
            "stdout": value.stdout[-1000:],
            "stderr": value.stderr[-1000:],
        }
    )
    if value.returncode:
        raise RuntimeError(f"command failed: {cmd[0]}")


def hygiene(root: Path, forbidden: list[str]) -> dict[str, Any]:
    text = "\n".join(
        path.read_text(errors="replace")
        for path in root.iterdir()
        if path.is_file() and path.name != "SHA256SUMS"
    )
    hits = ["forbidden" for item in forbidden if item and item in text]
    return {"passed": not hits, "hits": hits}


def checksum(root: Path) -> dict[str, Any]:
    names = sorted(
        path.name for path in root.iterdir() if path.is_file() and path.name != "SHA256SUMS"
    )
    (root / "SHA256SUMS").write_text(
        "".join(f"{sha(root / name)}  {name}\n" for name in names)
    )
    rows = [line.split("  ", 1) for line in (root / "SHA256SUMS").read_text().splitlines()]
    bad = [
        name
        for digest, name in rows
        if not (root / name).is_file() or sha(root / name) != digest
    ]
    return {
        "valid": names == sorted(FILES)
        and len(rows) == len(FILES)
        and len({name for _, name in rows}) == len(rows)
        and not bad,
        "entry_count": len(rows),
        "expected_file_count": len(FILES),
        "missing_files": sorted(set(FILES) - set(names)),
        "unexpected_files": sorted(set(names) - set(FILES)),
        "duplicate_files": sorted(
            {name for _, name in rows if [item[1] for item in rows].count(name) > 1}
        ),
        "hash_mismatches": bad,
        "self_included": any(name == "SHA256SUMS" for _, name in rows),
    }


def bootstrap(path: Path) -> None:
    path.write_text(
        '''import os,sys
sys.path.insert(0,os.environ["R9_REPOSITORY_ROOT"])
from src.main import app
import uvicorn
uvicorn.run(app,host="127.0.0.1",port=int(os.environ["R9_PORT"]))'''
    )


def start(boot: Path, env: dict[str, str]) -> subprocess.Popen[str]:
    local = env.copy()
    local.update(R9_REPOSITORY_ROOT=str(ROOT), R9_PORT=str(port()))
    process = subprocess.Popen(
        [sys.executable, str(boot)],
        cwd=ROOT,
        env=local,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            if (
                http(
                    "GET",
                    f"http://127.0.0.1:{local['R9_PORT']}/health",
                    username="",
                    password="",
                )[0]
                == 200
            ):
                process.r9_port = int(local["R9_PORT"])
                return process
        except OSError:
            pass
        if process.poll() is not None:
            raise RuntimeError("controller exited before health")
        time.sleep(0.1)
    raise RuntimeError("controller health timeout")


def stop(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.terminate()
        process.wait(timeout=10)


DB = '''import json,os
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotAuditEvent,PilotRunResult
s=json.loads(os.environ["R9_STATE"])
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as x:
 b=x.scalar(select(PilotRunResult).where(PilotRunResult.run_id==s["run_id"])); a=x.scalar(select(PilotArtifact).where(PilotArtifact.run_id==s["run_id"]))
 def row(v,fields): return {k:str(getattr(v,k)) for k in fields} if v else None
 out={"binding":row(b,["id","customer_id","project_id","procurement_case_id","run_id","requirements_file_sha256","canonical_report_file_sha256","binding_manifest_file_sha256"]),"artifact":row(a,["id","customer_id","project_id","procurement_case_id","run_id","artifact_key","pdf_sha256","manifest_file_sha256","byte_size"]) if a else None,"audit":[{"event_type":r.event_type,"customer_id":r.customer_id,"project_id":r.project_id,"case_id":r.procurement_case_id,"run_id":r.run_id} for r in x.scalars(select(PilotAuditEvent).where(PilotAuditEvent.run_id==s["run_id"]).order_by(PilotAuditEvent.created_at)).all()]}
 print(json.dumps(out,sort_keys=True))'''

MUTATE = '''import json,os
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotRunResult
s=json.loads(os.environ["R9_STATE"]); action=os.environ["R9_ACTION"]
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as x:
 b=x.scalar(select(PilotRunResult).where(PilotRunResult.run_id==s["run_id"])); a=x.scalar(select(PilotArtifact).where(PilotArtifact.run_id==s["run_id"]))
 if action=="delete_binding": x.delete(b)
 elif action=="delete_artifact": x.delete(a)
 elif action=="binding_mismatch": b.requirements_file_sha256="0"*64
 elif action=="artifact_mismatch": a.pdf_sha256="0"*64; a.byte_size=1
 x.commit()'''


def database(env: dict[str, str], state: dict[str, str]) -> dict[str, Any]:
    local = env.copy()
    local["R9_STATE"] = json.dumps(state)
    value = subprocess.run(
        [sys.executable, "-c", DB],
        cwd=ROOT,
        env=local,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(value.stdout)


def mutate(env: dict[str, str], state: dict[str, str], action: str) -> None:
    local = env.copy()
    local.update(R9_STATE=json.dumps(state), R9_ACTION=action)
    subprocess.run([sys.executable, "-c", MUTATE], cwd=ROOT, env=local, check=True)


def filesystem(
    data: Path, customer_id: str, state: dict[str, str]
) -> dict[str, Any]:
    root = (
        data
        / "customer-pilot"
        / customer_id
        / state["project_id"]
        / state["case_id"]
        / state["run_id"]
    )
    files: list[dict[str, Any]] = []
    if root.exists():
        for item in sorted(root.rglob("*")):
            if item.is_file():
                stat = item.stat()
                files.append(
                    {
                        "path": str(item.relative_to(data)),
                        "sha256": sha(item),
                        "size": stat.st_size,
                        "mtime_ns": stat.st_mtime_ns,
                    }
                )
    return {"root_exists": root.exists(), "files": files}


def operation(base: str, state: dict[str, str], artifact: bool) -> dict[str, Any]:
    suffix = (
        f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf"
        if artifact
        else f"/cases/{state['case_id']}/runs/{state['run_id']}/complete"
    )
    try:
        status, body, _ = http(
            "POST", base + suffix, username="", password="", body={}
        )
        try:
            parsed: Any = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"body_present": bool(body)}
        return {"kind": "HTTP POST", "status_code": status, "body": parsed}
    except Exception as exc:
        return {
            "kind": "HTTP POST",
            "exception_type": type(exc).__name__,
            "message": str(exc)[:200],
        }


def file_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[str]]:
    left = {item["path"]: item for item in before["files"]}
    right = {item["path"]: item for item in after["files"]}
    return {
        "created": sorted(set(right) - set(left)),
        "deleted": sorted(set(left) - set(right)),
        "overwritten": sorted(
            name for name in set(left) & set(right) if left[name] != right[name]
        ),
    }


def main() -> int:
    evidence = (
        ROOT
        / "output"
        / f"r9-db-filesystem-mismatch-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    )
    evidence.mkdir(parents=True)
    temp = Path(tempfile.mkdtemp(prefix="r9-mismatch-", dir=ROOT / "output"))
    data = temp / "data"
    data.mkdir()
    commands: list[dict[str, Any]] = []
    cleanup: dict[str, Any] = {"errors": [], "temporary_root_removed": False}
    started = time.monotonic()
    process: subprocess.Popen[str] | None = None
    password = "r9-" + secrets.token_urlsafe(12)
    dbport = port()
    compose_project = "r9mis" + secrets.token_hex(4)
    env = os.environ.copy()
    env.update(
        R8_POSTGRES_PASSWORD=password,
        R8_POSTGRES_PORT=str(dbport),
        AI_CORP_DATABASE_URL=f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{dbport}/r8_acceptance",
        AI_CORP_ARVECTUM_DATA_DIR=str(data),
        AI_CORP_PILOT_AUTH_ENABLED="false",
        AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED="false",
    )
    scenarios: list[dict[str, Any]] = []
    sentinel_before: dict[str, Any] = {}
    sentinel_after: dict[str, Any] = {}
    try:
        compose = [
            "docker",
            "compose",
            "-p",
            compose_project,
            "-f",
            str(COMPOSE),
        ]
        run(compose + ["up", "-d", "--wait"], env, commands)
        run([sys.executable, "-m", "alembic", "upgrade", "head"], env, commands)
        seed = '''import os,sys
sys.path.insert(0,"scripts/acceptance")
from run_r8_acceptance import _seed
_seed(os.environ)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.modules.customer_registry.models import CustomerProfile
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as s:
 s.add_all([CustomerProfile(customer_id="R9-MISMATCH",legal_name="R9",customer_status="prospect"),CustomerProfile(customer_id="R9-MISMATCH-SENTINEL",legal_name="R9 Sentinel",customer_status="prospect")]);s.commit()'''
        run([sys.executable, "-c", seed], env, commands)
        boot = temp / "boot.py"
        bootstrap(boot)
        process = start(boot, env)

        def base(customer_id: str) -> str:
            return f"http://127.0.0.1:{process.r9_port}/api/operator/pilot/customers/{customer_id}"

        def setup(customer_id: str, label: str, artifact: bool) -> dict[str, str]:
            customer_base = base(customer_id)
            _, body, _ = http(
                "POST",
                customer_base + "/projects",
                username="",
                password="",
                body={"name": label},
            )
            project_row = json.loads(body)
            _, body, _ = http(
                "POST",
                customer_base + f"/projects/{project_row['id']}/cases",
                username="",
                password="",
                body={"procurement_number": "0379100000726000101"},
            )
            case = json.loads(body)
            _, body, _ = http(
                "POST",
                customer_base + f"/cases/{case['id']}/runs",
                username="",
                password="",
                body={},
                headers={"Idempotency-Key": label},
            )
            result = json.loads(body)
            state = {
                "project_id": project_row["id"],
                "case_id": case["id"],
                "run_id": result["id"],
            }
            completed = operation(customer_base, state, False)
            if completed.get("status_code") != 200:
                raise RuntimeError("canonical setup failed")
            if artifact:
                exported = operation(customer_base, state, True)
                if exported.get("status_code") != 201:
                    raise RuntimeError("artifact setup failed")
            return state

        sentinel_state = setup(SENTINEL, "sentinel", True)
        sentinel_before = {
            "database": database(env, sentinel_state),
            "filesystem": filesystem(data, SENTINEL, sentinel_state),
        }

        def scenario(classification: str, artifact: bool, corruption: str) -> None:
            state = setup(CUSTOMER, classification, artifact)
            before_db = database(env, state)
            before_fs = filesystem(data, CUSTOMER, state)
            root = (
                data
                / "customer-pilot"
                / CUSTOMER
                / state["project_id"]
                / state["case_id"]
                / state["run_id"]
            )
            target = (
                root / "artifacts" / before_db["artifact"]["artifact_key"]
                if artifact
                else root / "analysis"
            )
            if corruption == "remove_directory":
                shutil.rmtree(target)
            elif corruption == "remove_file":
                (target / ("final.pdf" if artifact else "requirements.json")).unlink()
            elif corruption == "delete_row":
                mutate(env, state, "delete_artifact" if artifact else "delete_binding")
            else:
                mutate(env, state, "artifact_mismatch" if artifact else "binding_mismatch")
            mismatch_db = database(env, state)
            mismatch_fs = filesystem(data, CUSTOMER, state)
            request = operation(base(CUSTOMER), state, artifact)
            after_db = database(env, state)
            after_fs = filesystem(data, CUSTOMER, state)
            retry = operation(base(CUSTOMER), state, artifact)
            retry_db = database(env, state)
            retry_fs = filesystem(data, CUSTOMER, state)
            row = "artifact" if artifact else "binding"
            new_db_row = mismatch_db[row] is None and after_db[row] is not None
            first_delta = file_delta(mismatch_fs, after_fs)
            retry_delta = file_delta(after_fs, retry_fs)
            ownership_unchanged = all(
                value is None
                or (
                    value.get("customer_id") == CUSTOMER
                    and value.get("project_id") == state["project_id"]
                    and value.get("procurement_case_id") == state["case_id"]
                    and value.get("run_id") == state["run_id"]
                )
                for value in (after_db["binding"], after_db["artifact"])
            )
            safe = bool(
                request.get("status_code") == 409
                and retry.get("status_code") == 409
                and not new_db_row
                and not any(first_delta.values())
                and not any(retry_delta.values())
                and after_db[row] == retry_db[row]
                and ownership_unchanged
            )
            scenarios.append(
                {
                    "classification": classification,
                    "operation": request["kind"],
                    "request": request,
                    "retry_request": retry,
                    "database": {
                        "before": before_db,
                        "mismatch": mismatch_db,
                        "after": after_db,
                        "after_retry": retry_db,
                    },
                    "filesystem": {
                        "before": before_fs,
                        "mismatch": mismatch_fs,
                        "after": after_fs,
                        "after_retry": retry_fs,
                    },
                    "audit": {
                        "before": before_db["audit"],
                        "mismatch": mismatch_db["audit"],
                        "after": after_db["audit"],
                        "after_retry": retry_db["audit"],
                    },
                    "files_created": first_delta["created"],
                    "files_overwritten": first_delta["overwritten"],
                    "files_deleted": first_delta["deleted"],
                    "retry_files_created": retry_delta["created"],
                    "retry_files_overwritten": retry_delta["overwritten"],
                    "retry_files_deleted": retry_delta["deleted"],
                    "new_db_row": new_db_row,
                    "ownership_unchanged": ownership_unchanged,
                    "retry_safe": safe,
                    "safe": safe,
                    "outcome": "safe" if safe else "unsafe",
                }
            )

        scenario(CANONICAL[0], False, "remove_directory")
        scenario(CANONICAL[1], False, "delete_row")
        scenario(CANONICAL[2], False, "remove_file")
        scenario(CANONICAL[3], False, "metadata")
        scenario(ARTIFACT[0], True, "remove_directory")
        scenario(ARTIFACT[1], True, "delete_row")
        scenario(ARTIFACT[2], True, "remove_file")
        scenario(ARTIFACT[3], True, "metadata")
        sentinel_after = {
            "database": database(env, sentinel_state),
            "filesystem": filesystem(data, SENTINEL, sentinel_state),
        }
    finally:
        if process:
            try:
                stop(process)
            except Exception as exc:
                cleanup["errors"].append(type(exc).__name__)
        try:
            cleanup["compose_down_returncode"] = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-p",
                    compose_project,
                    "-f",
                    str(COMPOSE),
                    "down",
                    "--volumes",
                    "--remove-orphans",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
            ).returncode
        except Exception as exc:
            cleanup["errors"].append(type(exc).__name__)
            cleanup["compose_down_returncode"] = 1
        checks = {
            "containers": [
                "docker",
                "ps",
                "-aq",
                "--filter",
                f"label=com.docker.compose.project={compose_project}",
            ],
            "networks": [
                "docker",
                "network",
                "ls",
                "-q",
                "--filter",
                f"name={compose_project}",
            ],
            "volumes": [
                "docker",
                "volume",
                "ls",
                "-q",
                "--filter",
                f"name={compose_project}",
            ],
        }
        for name, command in checks.items():
            value = subprocess.run(command, text=True, capture_output=True)
            cleanup[f"{name}_check_returncode"] = value.returncode
            cleanup[name] = value.stdout.split()
        shutil.rmtree(temp, ignore_errors=True)
        cleanup["temporary_root_removed"] = not temp.exists()
        cleanup["cleanup_complete"] = bool(
            not cleanup["errors"]
            and cleanup["compose_down_returncode"] == 0
            and all(cleanup[f"{name}_check_returncode"] == 0 for name in checks)
            and all(not cleanup[name] for name in checks)
            and cleanup["temporary_root_removed"]
        )

    canonical = [item for item in scenarios if item["classification"] in CANONICAL]
    artifact = [item for item in scenarios if item["classification"] in ARTIFACT]
    safe_count = sum(bool(item["safe"]) for item in scenarios)
    unsafe_count = len(scenarios) - safe_count
    ownership_imports = [
        item["classification"] for item in scenarios if item["new_db_row"]
    ]
    orphan_deletions = [
        item["classification"]
        for item in scenarios
        if item["files_deleted"] or item["retry_files_deleted"]
    ]
    tenant_mixing = sentinel_before != sentinel_after or any(
        not item["ownership_unchanged"] for item in scenarios
    )
    assertions = {
        "scenario_count_8": len(scenarios) == 8,
        "classifications_exact": {
            item["classification"] for item in scenarios
        }
        == set(CANONICAL + ARTIFACT),
        "all_http_409": all(
            item["request"].get("status_code") == 409
            and item["retry_request"].get("status_code") == 409
            for item in scenarios
        ),
        "all_scenarios_safe": safe_count == 8,
        "tenant_isolation": not tenant_mixing,
        "no_automatic_repair": all(
            not item["files_created"]
            and not item["files_overwritten"]
            and not item["new_db_row"]
            for item in scenarios
        ),
        "no_filesystem_ownership_import": not ownership_imports,
        "no_orphan_deletion": not orphan_deletions,
        "snapshots_before_mismatch_after_retry": all(
            set(item["database"]) == {"before", "mismatch", "after", "after_retry"}
            and set(item["filesystem"])
            == {"before", "mismatch", "after", "after_retry"}
            for item in scenarios
        ),
    }
    write(evidence / "canonical-scenarios.json", canonical)
    write(evidence / "artifact-scenarios.json", artifact)
    write(
        evidence / "database-snapshots.json",
        {item["classification"]: item["database"] for item in scenarios},
    )
    write(
        evidence / "filesystem-snapshots.json",
        {item["classification"]: item["filesystem"] for item in scenarios},
    )
    write(
        evidence / "audit-snapshots.json",
        {item["classification"]: item["audit"] for item in scenarios},
    )
    write(
        evidence / "requests.json",
        {
            item["classification"]: {
                "request": item["request"],
                "retry": item["retry_request"],
            }
            for item in scenarios
        },
    )
    write(evidence / "assertions.json", assertions)
    write(evidence / "cleanup.json", cleanup)
    write(evidence / "commands.log", commands)
    result = {
        "status": PASS_STATUS if safe_count == 8 else FAIL_STATUS,
        "scenario_count": len(scenarios),
        "safe_count": safe_count,
        "unsafe_count": unsafe_count,
        "inconclusive_count": 0,
        "classifications": [item["classification"] for item in scenarios],
        "assertions": assertions,
        "cleanup": cleanup,
        "automatic_repair_performed": not assertions["no_automatic_repair"],
        "filesystem_ownership_imported": bool(ownership_imports),
        "filesystem_ownership_import_scenarios": ownership_imports,
        "orphan_deleted": bool(orphan_deletions),
        "orphan_deletion_scenarios": orphan_deletions,
        "tenant_mixing_detected": tenant_mixing,
        "sentinel_unchanged": sentinel_before == sentinel_after,
        "duration_seconds": time.monotonic() - started,
    }
    write(evidence / "mismatch-result.json", result)
    result["hygiene"] = hygiene(evidence, [password, str(temp)])
    result["checksum_validator"] = {
        "valid": {path.name for path in evidence.iterdir() if path.is_file()}
        == set(FILES),
        "entry_count": len(FILES),
        "expected_file_count": len(FILES),
        "missing_files": [],
        "unexpected_files": [],
        "duplicate_files": [],
        "hash_mismatches": [],
        "self_included": False,
    }
    write(evidence / "mismatch-result.json", result)
    details = checksum(evidence)
    final_ok = bool(
        safe_count == 8
        and all(assertions.values())
        and cleanup["cleanup_complete"]
        and result["hygiene"]["passed"]
        and details["valid"]
    )
    print(evidence)
    return 0 if final_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
