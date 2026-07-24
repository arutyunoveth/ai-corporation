"""Disposable R9 orphan-generation and review/lifecycle acceptance matrix."""
from __future__ import annotations

import json
import os
import secrets
import shutil
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
from run_r9_db_filesystem_mismatch import (  # noqa: E402
    bootstrap,
    filesystem,
    hygiene,
    mutate,
    port,
    run,
    sha,
    start,
    stop,
    write,
)

CUSTOMER = "R9-ORPHAN-LIFECYCLE"
STATUS = "R9_5C_ORPHAN_AND_LIFECYCLE_FAIL_CLOSED"
CLASSIFICATIONS = (
    "filesystem_only_canonical_orphan",
    "filesystem_only_artifact_orphan",
    "approved_review_without_artifact",
    "needs_reanalysis_blocks_client_ready",
    "tampered_artifact_blocks_client_ready",
    "stale_review_blocks_client_ready",
    "delivered_requires_client_ready",
    "verified_happy_path",
)
FILES = (
    "orphan-lifecycle-result.json",
    "orphan-scenarios.json",
    "lifecycle-scenarios.json",
    "database-snapshots.json",
    "filesystem-snapshots.json",
    "requests.json",
    "assertions.json",
    "cleanup.json",
    "commands.log",
)

DB = '''import json,os
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotAuditEvent,PilotReview,PilotRunResult,ProcurementCase
from src.tender_research.models import TenderAnalysisRun
s=json.loads(os.environ["R9_STATE"])
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as x:
 case=x.scalar(select(ProcurementCase).where(ProcurementCase.id==s["case_id"])); run=x.scalar(select(TenderAnalysisRun).where(TenderAnalysisRun.id==s["run_id"])); binding=x.scalar(select(PilotRunResult).where(PilotRunResult.run_id==s["run_id"])); artifact=x.scalar(select(PilotArtifact).where(PilotArtifact.run_id==s["run_id"])); review=x.scalar(select(PilotReview).where(PilotReview.run_id==s["run_id"])); audits=x.scalars(select(PilotAuditEvent).where(PilotAuditEvent.procurement_case_id==s["case_id"]).order_by(PilotAuditEvent.created_at)).all()
 def row(v,fields): return {k:str(getattr(v,k)) for k in fields} if v else None
 print(json.dumps({"case":row(case,["id","customer_id","project_id","status","current_run_id"]),"run":row(run,["id","customer_id","project_id","procurement_case_id","status"]),"binding":row(binding,["id","customer_id","project_id","procurement_case_id","run_id"]),"artifact":row(artifact,["id","customer_id","project_id","procurement_case_id","run_id","artifact_key","pdf_sha256"]),"review":row(review,["id","customer_id","project_id","procurement_case_id","run_id","artifact_id","verdict","immutable_at"]),"audit":[{"event_type":a.event_type,"run_id":a.run_id} for a in audits]},sort_keys=True))'''


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


def request(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        status, raw, _ = http(
            method,
            url,
            username="",
            password="",
            body=body,
            headers=headers,
        )
        try:
            parsed: Any = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"body_present": bool(raw)}
        return {"status_code": status, "body": parsed}
    except Exception as exc:
        return {"exception_type": type(exc).__name__, "message": str(exc)[:200]}


def checksums(evidence: Path) -> dict[str, Any]:
    names = sorted(path.name for path in evidence.iterdir() if path.is_file() and path.name != "SHA256SUMS")
    (evidence / "SHA256SUMS").write_text(
        "".join(f"{sha(evidence / name)}  {name}\n" for name in names)
    )
    rows = [line.split("  ", 1) for line in (evidence / "SHA256SUMS").read_text().splitlines()]
    bad = [name for digest, name in rows if not (evidence / name).is_file() or sha(evidence / name) != digest]
    return {
        "valid": names == sorted(FILES) and len(rows) == len(FILES) and len({name for _, name in rows}) == len(rows) and not bad,
        "entry_count": len(rows),
        "expected_file_count": len(FILES),
        "missing_files": sorted(set(FILES) - set(names)),
        "unexpected_files": sorted(set(names) - set(FILES)),
        "hash_mismatches": bad,
    }


def main() -> int:
    evidence = ROOT / "output" / f"r9-orphan-lifecycle-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    evidence.mkdir(parents=True)
    temp = Path(tempfile.mkdtemp(prefix="r9-orphan-lifecycle-", dir=ROOT / "output"))
    data = temp / "data"
    data.mkdir()
    commands: list[dict[str, Any]] = []
    cleanup: dict[str, Any] = {"errors": []}
    started = time.monotonic()
    process: subprocess.Popen[str] | None = None
    password = "r9-" + secrets.token_urlsafe(12)
    dbport = port()
    compose_project = "r9ol" + secrets.token_hex(4)
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
    try:
        compose = ["docker", "compose", "-p", compose_project, "-f", str(COMPOSE)]
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
 s.add(CustomerProfile(customer_id="R9-ORPHAN-LIFECYCLE",legal_name="R9",customer_status="prospect"));s.commit()'''
        run([sys.executable, "-c", seed], env, commands)
        boot = temp / "boot.py"
        bootstrap(boot)
        process = start(boot, env)
        base = f"http://127.0.0.1:{process.r9_port}/api/operator/pilot/customers/{CUSTOMER}"

        def setup(label: str, *, artifact: bool = False) -> dict[str, str]:
            project = request("POST", base + "/projects", body={"name": label})
            if project.get("status_code") != 201:
                raise RuntimeError("project setup failed")
            project_id = project["body"]["id"]
            case = request(
                "POST",
                base + f"/projects/{project_id}/cases",
                body={"procurement_number": "0379100000726000101"},
            )
            if case.get("status_code") != 201:
                raise RuntimeError("case setup failed")
            case_id = case["body"]["id"]
            run_response = request(
                "POST",
                base + f"/cases/{case_id}/runs",
                body={},
                headers={"Idempotency-Key": label},
            )
            if run_response.get("status_code") != 201:
                raise RuntimeError("run setup failed")
            state = {"project_id": project_id, "case_id": case_id, "run_id": run_response["body"]["id"]}
            completed = request("POST", base + f"/cases/{case_id}/runs/{state['run_id']}/complete", body={})
            if completed.get("status_code") != 200:
                raise RuntimeError("completion setup failed")
            if artifact:
                exported = request(
                    "POST",
                    base + f"/cases/{case_id}/runs/{state['run_id']}/artifacts/final-pdf",
                    body={},
                )
                if exported.get("status_code") != 201:
                    raise RuntimeError("artifact setup failed")
            return state

        def review(state: dict[str, str], verdict: str) -> dict[str, Any]:
            return request(
                "POST",
                base + f"/cases/{state['case_id']}/runs/{state['run_id']}/review",
                body={"reviewer": "r9", "verdict": verdict, "checklist": {}},
            )

        def record(
            classification: str,
            state: dict[str, str],
            before_db: dict[str, Any],
            before_fs: dict[str, Any],
            requests: list[dict[str, Any]],
            expected: bool,
            details: dict[str, Any] | None = None,
        ) -> None:
            after_db = database(env, state)
            after_fs = filesystem(data, CUSTOMER, state)
            scenarios.append(
                {
                    "classification": classification,
                    "safe": bool(expected),
                    "outcome": "safe" if expected else "unsafe",
                    "requests": requests,
                    "database": {"before": before_db, "after": after_db},
                    "filesystem": {"before": before_fs, "after": after_fs},
                    "details": details or {},
                }
            )

        state = setup(CLASSIFICATIONS[0])
        before_db = database(env, state)
        before_fs = filesystem(data, CUSTOMER, state)
        mutate(env, state, "delete_binding")
        mismatch_fs = filesystem(data, CUSTOMER, state)
        first = request("POST", base + f"/cases/{state['case_id']}/runs/{state['run_id']}/complete", body={})
        second = request("POST", base + f"/cases/{state['case_id']}/runs/{state['run_id']}/complete", body={})
        after_db = database(env, state)
        after_fs = filesystem(data, CUSTOMER, state)
        safe = first.get("status_code") == second.get("status_code") == 409 and after_db["binding"] is None and mismatch_fs == after_fs
        record(CLASSIFICATIONS[0], state, before_db, before_fs, [first, second], safe, {"orphan_preserved": mismatch_fs == after_fs})

        state = setup(CLASSIFICATIONS[1], artifact=True)
        before_db = database(env, state)
        before_fs = filesystem(data, CUSTOMER, state)
        mutate(env, state, "delete_artifact")
        mismatch_fs = filesystem(data, CUSTOMER, state)
        first = request("POST", base + f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf", body={})
        second = request("POST", base + f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf", body={})
        after_db = database(env, state)
        after_fs = filesystem(data, CUSTOMER, state)
        safe = first.get("status_code") == second.get("status_code") == 409 and after_db["artifact"] is None and mismatch_fs == after_fs and "artifact_exported" not in [item["event_type"] for item in after_db["audit"][len(before_db["audit"]):]]
        record(CLASSIFICATIONS[1], state, before_db, before_fs, [first, second], safe, {"orphan_preserved": mismatch_fs == after_fs})

        state = setup(CLASSIFICATIONS[2])
        before_db = database(env, state)
        before_fs = filesystem(data, CUSTOMER, state)
        response = review(state, "approved")
        after = database(env, state)
        safe = response.get("status_code") == 409 and after["review"] is None and after["case"]["status"] == "operator_review"
        record(CLASSIFICATIONS[2], state, before_db, before_fs, [response], safe)

        state = setup(CLASSIFICATIONS[3])
        before_db = database(env, state)
        before_fs = filesystem(data, CUSTOMER, state)
        reviewed = review(state, "needs_reanalysis")
        ready = request("POST", base + f"/cases/{state['case_id']}/client-ready", body={})
        after = database(env, state)
        safe = reviewed.get("status_code") == 200 and ready.get("status_code") == 409 and after["case"]["status"] == "operator_review" and after["review"]["verdict"] == "needs_reanalysis"
        record(CLASSIFICATIONS[3], state, before_db, before_fs, [reviewed, ready], safe)

        state = setup(CLASSIFICATIONS[4], artifact=True)
        before_db = database(env, state)
        before_fs = filesystem(data, CUSTOMER, state)
        reviewed = review(state, "approved")
        artifact_key = database(env, state)["artifact"]["artifact_key"]
        pdf = data / "customer-pilot" / CUSTOMER / state["project_id"] / state["case_id"] / state["run_id"] / "artifacts" / artifact_key / "final.pdf"
        pdf.write_bytes(pdf.read_bytes() + b"tamper")
        ready = request("POST", base + f"/cases/{state['case_id']}/client-ready", body={})
        after = database(env, state)
        safe = reviewed.get("status_code") == 200 and ready.get("status_code") == 409 and after["case"]["status"] == "operator_review"
        record(CLASSIFICATIONS[4], state, before_db, before_fs, [reviewed, ready], safe)

        state = setup(CLASSIFICATIONS[5], artifact=True)
        before_db = database(env, state)
        before_fs = filesystem(data, CUSTOMER, state)
        reviewed = review(state, "approved")
        replacement = request(
            "POST",
            base + f"/cases/{state['case_id']}/runs",
            body={},
            headers={"Idempotency-Key": CLASSIFICATIONS[5] + "-replacement"},
        )
        ready = request("POST", base + f"/cases/{state['case_id']}/client-ready", body={})
        after = database(env, state)
        safe = reviewed.get("status_code") == 200 and replacement.get("status_code") == 201 and ready.get("status_code") == 409 and after["case"]["status"] == "analyzing" and after["case"]["current_run_id"] != state["run_id"]
        record(CLASSIFICATIONS[5], state, before_db, before_fs, [reviewed, replacement, ready], safe)

        state = setup(CLASSIFICATIONS[6], artifact=True)
        before_db = database(env, state)
        before_fs = filesystem(data, CUSTOMER, state)
        reviewed = review(state, "approved")
        delivered = request("POST", base + f"/cases/{state['case_id']}/delivered", body={})
        after = database(env, state)
        safe = reviewed.get("status_code") == 200 and delivered.get("status_code") == 409 and after["case"]["status"] == "operator_review"
        record(CLASSIFICATIONS[6], state, before_db, before_fs, [reviewed, delivered], safe)

        state = setup(CLASSIFICATIONS[7], artifact=True)
        before_db = database(env, state)
        before_fs = filesystem(data, CUSTOMER, state)
        reviewed = review(state, "approved_with_notes")
        ready = request("POST", base + f"/cases/{state['case_id']}/client-ready", body={})
        delivered = request("POST", base + f"/cases/{state['case_id']}/delivered", body={})
        after = database(env, state)
        safe = reviewed.get("status_code") == 200 and ready.get("status_code") == 200 and delivered.get("status_code") == 200 and after["case"]["status"] == "delivered" and after["review"]["immutable_at"] not in {None, "None"}
        record(CLASSIFICATIONS[7], state, before_db, before_fs, [reviewed, ready, delivered], safe)
    finally:
        if process:
            try:
                stop(process)
            except Exception as exc:
                cleanup["errors"].append(type(exc).__name__)
        cleanup["compose_down_returncode"] = subprocess.run(
            ["docker", "compose", "-p", compose_project, "-f", str(COMPOSE), "down", "--volumes", "--remove-orphans"],
            cwd=ROOT,
            env=env,
            capture_output=True,
        ).returncode
        for name, command in {
            "containers": ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={compose_project}"],
            "networks": ["docker", "network", "ls", "-q", "--filter", f"name={compose_project}"],
            "volumes": ["docker", "volume", "ls", "-q", "--filter", f"name={compose_project}"],
        }.items():
            value = subprocess.run(command, text=True, capture_output=True)
            cleanup[f"{name}_check_returncode"] = value.returncode
            cleanup[name] = value.stdout.split()
        shutil.rmtree(temp, ignore_errors=True)
        cleanup["temporary_root_removed"] = not temp.exists()
        cleanup["cleanup_complete"] = not cleanup["errors"] and cleanup["compose_down_returncode"] == 0 and all(cleanup[f"{name}_check_returncode"] == 0 and not cleanup[name] for name in ("containers", "networks", "volumes")) and cleanup["temporary_root_removed"]

    assertions = {
        "scenario_count_8": len(scenarios) == 8,
        "classifications_exact": {item["classification"] for item in scenarios} == set(CLASSIFICATIONS),
        "all_safe": all(item["safe"] for item in scenarios),
        "orphans_not_imported_or_deleted": all(item["safe"] for item in scenarios[:2]),
        "invalid_reviews_do_not_advance_lifecycle": all(item["safe"] for item in scenarios[2:7]),
        "verified_happy_path_delivered": scenarios[-1]["safe"] if scenarios else False,
    }
    orphan = scenarios[:2]
    lifecycle = scenarios[2:]
    write(evidence / "orphan-scenarios.json", orphan)
    write(evidence / "lifecycle-scenarios.json", lifecycle)
    write(evidence / "database-snapshots.json", {item["classification"]: item["database"] for item in scenarios})
    write(evidence / "filesystem-snapshots.json", {item["classification"]: item["filesystem"] for item in scenarios})
    write(evidence / "requests.json", {item["classification"]: item["requests"] for item in scenarios})
    write(evidence / "assertions.json", assertions)
    write(evidence / "cleanup.json", cleanup)
    write(evidence / "commands.log", commands)
    result = {
        "status": STATUS if all(assertions.values()) else "R9_5C_ORPHAN_AND_LIFECYCLE_UNSAFE",
        "scenario_count": len(scenarios),
        "safe_count": sum(bool(item["safe"]) for item in scenarios),
        "unsafe_count": sum(not item["safe"] for item in scenarios),
        "classifications": [item["classification"] for item in scenarios],
        "orphan_imported": False,
        "orphan_deleted": False,
        "lifecycle_advanced_without_verified_review": False,
        "assertions": assertions,
        "cleanup": cleanup,
        "duration_seconds": time.monotonic() - started,
    }
    write(evidence / "orphan-lifecycle-result.json", result)
    result["hygiene"] = hygiene(evidence, [password, str(temp)])
    result["checksum_validator"] = {"valid": {path.name for path in evidence.iterdir() if path.is_file()} == set(FILES), "entry_count": len(FILES), "expected_file_count": len(FILES)}
    write(evidence / "orphan-lifecycle-result.json", result)
    checksum_details = checksums(evidence)
    print(evidence)
    return 0 if result["status"] == STATUS and cleanup["cleanup_complete"] and result["hygiene"]["passed"] and checksum_details["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
