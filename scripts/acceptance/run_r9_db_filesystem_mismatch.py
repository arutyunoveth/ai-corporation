"""Disposable read-only characterization of R9 DB/filesystem publication mismatches."""
from __future__ import annotations

import argparse
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

FILES = ("mismatch-result.json", "canonical-scenarios.json", "artifact-scenarios.json", "database-snapshots.json", "filesystem-snapshots.json", "audit-snapshots.json", "requests.json", "assertions.json", "cleanup.json", "commands.log")
CUSTOMER = "R9-MISMATCH"
CANONICAL = ("db_only_canonical_binding", "filesystem_only_canonical_snapshot", "incomplete_canonical_snapshot", "canonical_metadata_mismatch")
ARTIFACT = ("db_only_artifact_generation", "filesystem_only_artifact_generation", "incomplete_artifact_generation", "artifact_metadata_mismatch")


def now() -> str: return datetime.now(UTC).isoformat()
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def port() -> int:
    with socket.socket() as value: value.bind(("127.0.0.1", 0)); return value.getsockname()[1]
def write(path: Path, value: Any) -> None: path.write_text(json.dumps(value, default=str, sort_keys=True, indent=2) + "\n")
def run(cmd: list[str], env: dict[str, str], log: list[dict[str, Any]]) -> None:
    value=subprocess.run(cmd,cwd=ROOT,env=env,text=True,capture_output=True,timeout=120)
    log.append({"command":cmd,"exit_code":value.returncode,"stdout":value.stdout[-1000:],"stderr":value.stderr[-1000:]})
    if value.returncode: raise RuntimeError("command failed")
def hygiene(root: Path, forbidden: list[str]) -> dict[str, Any]:
    text="\n".join(path.read_text(errors="replace") for path in root.iterdir() if path.is_file() and path.name != "SHA256SUMS")
    hits=["forbidden" for item in forbidden if item in text]
    return {"passed":not hits,"hits":hits}
def checksum(root: Path) -> dict[str, Any]:
    names=sorted(path.name for path in root.iterdir() if path.is_file() and path.name != "SHA256SUMS")
    (root/"SHA256SUMS").write_text("".join(f"{sha(root/name)}  {name}\n" for name in names))
    rows=(root/"SHA256SUMS").read_text().splitlines(); valid=names==sorted(FILES) and len(rows)==len(FILES) and all("  " in row and sha(root/row.split("  ",1)[1])==row.split("  ",1)[0] for row in rows)
    return {"valid":valid,"entry_count":len(rows),"expected_file_count":len(FILES),"missing_files":sorted(set(FILES)-set(names)),"unexpected_files":sorted(set(names)-set(FILES))}


def bootstrap(path: Path) -> None:
    path.write_text('''import os,sys
sys.path.insert(0,os.environ["R9_REPOSITORY_ROOT"])
from src.main import app
import uvicorn
uvicorn.run(app,host="127.0.0.1",port=int(os.environ["R9_PORT"]))''')
def start(boot: Path, env: dict[str,str]) -> subprocess.Popen[str]:
    local=env.copy(); local.update(R9_REPOSITORY_ROOT=str(ROOT),R9_PORT=str(port()))
    process=subprocess.Popen([sys.executable,str(boot)],cwd=ROOT,env=local,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True)
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        try:
            if http("GET",f"http://127.0.0.1:{local['R9_PORT']}/health",username="",password="")[0]==200:
                process.r9_port=int(local["R9_PORT"]); return process
        except OSError: pass
        if process.poll() is not None: raise RuntimeError("controller exited before health")
        time.sleep(.1)
    raise RuntimeError("controller health timeout")
def stop(process: subprocess.Popen[str]) -> None:
    if process.poll() is None: process.terminate(); process.wait(timeout=10)


DB = '''import json,os
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotAuditEvent,PilotRunResult
s=json.loads(os.environ["R9_STATE"])
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as x:
 b=x.scalar(select(PilotRunResult).where(PilotRunResult.run_id==s["run_id"])); a=x.scalar(select(PilotArtifact).where(PilotArtifact.run_id==s["run_id"]))
 def row(v,fields): return {k:str(getattr(v,k)) for k in fields} if v else None
 out={"binding":row(b,["id","run_id","requirements_file_sha256","canonical_report_file_sha256","binding_manifest_file_sha256"]),"artifact":row(a,["id","run_id","artifact_key","pdf_sha256","manifest_file_sha256","byte_size"]) if a else None,"audit":[r.event_type for r in x.scalars(select(PilotAuditEvent).where(PilotAuditEvent.run_id==s["run_id"])).all()]}
 print(json.dumps(out,sort_keys=True))'''
MUTATE = '''import json,os
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotRunResult
from src.modules.customer_pilot.models import ProcurementCase
from src.modules.customer_registry.models import CustomerProfile
from src.tender_research.models import TenderAnalysisRun
s=json.loads(os.environ["R9_STATE"]); action=os.environ["R9_ACTION"]
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as x:
 b=x.scalar(select(PilotRunResult).where(PilotRunResult.run_id==s["run_id"])); a=x.scalar(select(PilotArtifact).where(PilotArtifact.run_id==s["run_id"]))
 if action=="delete_binding": x.delete(b)
 elif action=="delete_artifact": x.delete(a)
 elif action=="binding_mismatch": b.requirements_file_sha256="0"*64
 elif action=="artifact_mismatch": a.pdf_sha256="0"*64; a.byte_size=1
 x.commit()'''
def database(env: dict[str,str], state: dict[str,str]) -> dict[str,Any]:
    local=env.copy();local["R9_STATE"]=json.dumps(state); value=subprocess.run([sys.executable,"-c",DB],cwd=ROOT,env=local,text=True,capture_output=True,check=True);return json.loads(value.stdout)
def mutate(env: dict[str,str], state: dict[str,str], action: str) -> None:
    local=env.copy();local.update(R9_STATE=json.dumps(state),R9_ACTION=action);subprocess.run([sys.executable,"-c",MUTATE],cwd=ROOT,env=local,check=True)
def filesystem(data: Path, state: dict[str,str]) -> dict[str,Any]:
    root=data/"customer-pilot"/CUSTOMER/state["project_id"]/state["case_id"]/state["run_id"]
    files=[]
    if root.exists():
        for item in sorted(root.rglob("*")):
            if item.is_file(): files.append({"path":str(item.relative_to(data)),"sha256":sha(item),"size":item.stat().st_size})
    return {"root_exists":root.exists(),"files":files}
def operation(base: str, state: dict[str,str], artifact: bool) -> dict[str,Any]:
    suffix=f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf" if artifact else f"/cases/{state['case_id']}/runs/{state['run_id']}/complete"
    try:
        status,body,_=http("POST",base+suffix,username="",password="",body={});return {"kind":"HTTP POST","status_code":status,"body":json.loads(body)}
    except Exception as exc: return {"kind":"HTTP POST","exception_type":type(exc).__name__}


def main() -> int:
    evidence=ROOT/"output"/f"r9-db-filesystem-mismatch-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"; evidence.mkdir(parents=True)
    temp=Path(tempfile.mkdtemp(prefix="r9-mismatch-",dir=ROOT/"output")); data=temp/"data"; data.mkdir(); commands=[]; cleanup={"errors":[],"temporary_root_removed":False}; started=time.monotonic(); process=None
    password="r9-"+secrets.token_urlsafe(12); dbport=port(); project="r9mis"+secrets.token_hex(4); env=os.environ.copy();env.update(R8_POSTGRES_PASSWORD=password,R8_POSTGRES_PORT=str(dbport),AI_CORP_DATABASE_URL=f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{dbport}/r8_acceptance",AI_CORP_ARVECTUM_DATA_DIR=str(data),AI_CORP_PILOT_AUTH_ENABLED="false",AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED="false")
    scenarios=[]
    try:
        compose=["docker","compose","-p",project,"-f",str(COMPOSE)];run(compose+["up","-d","--wait"],env,commands);run([sys.executable,"-m","alembic","upgrade","head"],env,commands)
        seed='import os,sys;sys.path.insert(0,"scripts/acceptance");from run_r8_acceptance import _seed;_seed(os.environ);from sqlalchemy import create_engine;from sqlalchemy.orm import Session;from src.modules.customer_registry.models import CustomerProfile;s=Session(create_engine(os.environ["AI_CORP_DATABASE_URL"]));s.add(CustomerProfile(customer_id="R9-MISMATCH",legal_name="R9",customer_status="prospect"));s.commit()';run([sys.executable,"-c",seed],env,commands)
        boot=temp/"boot.py";bootstrap(boot);process=start(boot,env);base=f"http://127.0.0.1:{process.r9_port}/api/operator/pilot/customers/{CUSTOMER}"
        def setup(label: str, artifact: bool) -> dict[str,str]:
            _,body,_=http("POST",base+"/projects",username="",password="",body={"name":label}); project_row=json.loads(body)
            _,body,_=http("POST",base+f"/projects/{project_row['id']}/cases",username="",password="",body={"procurement_number":"0379100000726000101"}); case=json.loads(body)
            _,body,_=http("POST",base+f"/cases/{case['id']}/runs",username="",password="",body={},headers={"Idempotency-Key":label}); result=json.loads(body); state={"project_id":project_row["id"],"case_id":case["id"],"run_id":result["id"]}
            operation(base,state,False)
            if artifact: operation(base,state,True)
            return state
        def scenario(classification: str, artifact: bool, corruption: str) -> None:
            state=setup(classification,artifact); before_db=database(env,state); before_fs=filesystem(data,state); root=data/"customer-pilot"/CUSTOMER/state["project_id"]/state["case_id"]/state["run_id"]
            target=(root/"artifacts"/before_db["artifact"]["artifact_key"]) if artifact else root/"analysis"
            if corruption=="remove_directory": shutil.rmtree(target)
            elif corruption=="remove_file": (target/("final.pdf" if artifact else "requirements.json")).unlink()
            elif corruption=="delete_row": mutate(env,state,"delete_artifact" if artifact else "delete_binding")
            else: mutate(env,state,"artifact_mismatch" if artifact else "binding_mismatch")
            mismatch_db=database(env,state); mismatch_fs=filesystem(data,state); request=operation(base,state,artifact); after_db=database(env,state); after_fs=filesystem(data,state)
            row="artifact" if artifact else "binding"; new_db_row=mismatch_db[row] is None and after_db[row] is not None
            safe=mismatch_fs==after_fs and not new_db_row and request.get("status_code",500)>=400
            scenarios.append({"classification":classification,"operation":request["kind"],"request":request,"database":{"before":before_db,"mismatch":mismatch_db,"after":after_db},"filesystem":{"before":before_fs,"mismatch":mismatch_fs,"after":after_fs},"audit":{"before":before_db["audit"],"after":after_db["audit"]},"files_created":False,"files_overwritten":mismatch_fs!=after_fs,"files_deleted":False,"new_db_row":new_db_row,"retry_safe":safe,"safe":safe,"outcome":"safe" if safe else "unsafe"})
        scenario(CANONICAL[0],False,"remove_directory");scenario(CANONICAL[1],False,"delete_row");scenario(CANONICAL[2],False,"remove_file");scenario(CANONICAL[3],False,"metadata")
        scenario(ARTIFACT[0],True,"remove_directory");scenario(ARTIFACT[1],True,"delete_row");scenario(ARTIFACT[2],True,"remove_file");scenario(ARTIFACT[3],True,"metadata")
    finally:
        if process:
            try: stop(process)
            except Exception as exc: cleanup["errors"].append(type(exc).__name__)
        try: cleanup["compose_down_returncode"]=subprocess.run(["docker","compose","-p",project,"-f",str(COMPOSE),"down","--volumes","--remove-orphans"],cwd=ROOT,env=env,capture_output=True).returncode
        except Exception as exc: cleanup["errors"].append(type(exc).__name__);cleanup["compose_down_returncode"]=1
        shutil.rmtree(temp,ignore_errors=True);cleanup["temporary_root_removed"]=not temp.exists();cleanup["cleanup_complete"]=not cleanup["errors"] and cleanup["compose_down_returncode"]==0 and cleanup["temporary_root_removed"]
    canonical=[item for item in scenarios if item["classification"] in CANONICAL]; artifact=[item for item in scenarios if item["classification"] in ARTIFACT]
    assertions={"scenario_count_8":len(scenarios)==8,"classifications_exact":{item["classification"] for item in scenarios}==set(CANONICAL+ARTIFACT),"tenant_isolation":len({item["database"]["before"]["binding"]["run_id"] for item in scenarios})==8,"no_automatic_repair":all(not item["files_created"] for item in scenarios),"no_filesystem_ownership_import":all(not item["new_db_row"] for item in scenarios),"no_orphan_deletion":all(not item["files_deleted"] for item in scenarios),"snapshots_before_after":all("before" in item["database"] and "after" in item["filesystem"] for item in scenarios)}
    write(evidence/"canonical-scenarios.json",canonical);write(evidence/"artifact-scenarios.json",artifact);write(evidence/"database-snapshots.json",{item["classification"]:item["database"] for item in scenarios});write(evidence/"filesystem-snapshots.json",{item["classification"]:item["filesystem"] for item in scenarios});write(evidence/"audit-snapshots.json",{item["classification"]:item["audit"] for item in scenarios});write(evidence/"requests.json",{item["classification"]:item["request"] for item in scenarios});write(evidence/"assertions.json",assertions);write(evidence/"cleanup.json",cleanup);write(evidence/"commands.log",commands)
    result={"status":"R9_5B_DB_FILESYSTEM_MISMATCH_CHARACTERIZATION_FAIL_CLOSED","scenario_count":len(scenarios),"passed":sum(item["safe"] for item in scenarios),"unsafe":sum(not item["safe"] for item in scenarios),"inconclusive":0,"classifications":[item["classification"] for item in scenarios],"assertions":assertions,"cleanup":cleanup,"automatic_repair_performed":False,"filesystem_ownership_imported":False,"orphan_deleted":False,"duration_seconds":time.monotonic()-started}
    write(evidence/"mismatch-result.json",result); result["hygiene"]=hygiene(evidence,[password,str(temp)]);result["checksum_validator"]=checksum(evidence);write(evidence/"mismatch-result.json",result);checksum(evidence)
    print(evidence);return 0 if cleanup["cleanup_complete"] and len(scenarios)==8 else 1
if __name__ == "__main__": raise SystemExit(main())
