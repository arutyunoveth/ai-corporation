"""Raw disposable hard-kill evidence for R9.5 interrupted publication."""
from __future__ import annotations

import hashlib
import argparse
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "tests/integration/compose.r8-postgres.yml"
sys.path.insert(0, str(ROOT / "scripts" / "acceptance"))
from r8_acceptance.runtime import http  # noqa: E402

STATUS = "R9_5_INTERRUPTED_PUBLICATION_BOUNDARIES_CHARACTERIZED_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL"
FILES = ("interrupted-publication-result.json","fault-matrix-canonical.json","fault-matrix-artifact.json","canonical-pre-rename.json","canonical-post-rename.json","artifact-pre-rename.json","artifact-post-rename-same-bytes.json","artifact-post-rename-conflicting-bytes.json","database-snapshots.json","filesystem-snapshots.json","audit-snapshots.json","process-lifecycle.json","verifier-results.json","commands.log","backend-logs.json","cleanup.json")

CUSTOMER = "R9-INTERRUPTED"
SCENARIOS = (
    ("canonical-pre-rename", "canonical", "after_manifest_written", None, 200),
    ("canonical-post-rename", "canonical", "after_rename", None, 200),
    ("artifact-pre-rename", "artifact", "after_manifest_written", "A", 201),
    ("artifact-post-rename-same-bytes", "artifact", "after_rename", "A", 201),
    ("artifact-post-rename-conflicting-bytes", "artifact", "after_rename", "B", 409),
)


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def sanitize(value: Any) -> Any:
    if isinstance(value, dict): return {str(k): sanitize(v) for k,v in value.items()}
    if isinstance(value, list): return [sanitize(v) for v in value]
    if not isinstance(value, str): return value
    value=re.sub(r"postgres(?:ql)?(?:\+\w+)?://[^\s\"']+","<postgres-url>",value)
    value=re.sub(r"(?i)(password|authorization|cookie|token)\s*[=:]\s*[^\s,;\"']+",r"\1=<redacted>",value)
    return re.sub(r"/Users/[^\s\"']+/(?:output/)?r9-interrupted-[^\s\"']+","<temporary-root>",value)
def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(sanitize(value), default=str, sort_keys=True, indent=2) + "\n")
def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def checksums(evidence: Path) -> dict[str,Any]:
    present={p.name for p in evidence.iterdir() if p.is_file() and p.name!="SHA256SUMS"}; expected=set(FILES); missing=sorted(expected-present); unexpected=sorted(present-expected)
    if not missing and not unexpected: (evidence/"SHA256SUMS").write_text("".join(f"{digest(evidence/name)}  {name}\n" for name in sorted(expected)))
    rows=[line.split("  ",1) for line in (evidence/"SHA256SUMS").read_text().splitlines()] if (evidence/"SHA256SUMS").exists() else []
    names=[x[1] for x in rows if len(x)==2]; bad=[n for d,n in rows if len(n) and (not (evidence/n).is_file() or digest(evidence/n)!=d)]
    return {"valid":not missing and not unexpected and len(rows)==len(expected) and len(names)==len(set(names)) and set(names)==expected and not bad and "SHA256SUMS" not in names,"entry_count":len(rows),"expected_file_count":len(expected),"duplicate_files":sorted({x for x in names if names.count(x)>1}),"missing_files":missing,"unexpected_files":unexpected,"hash_mismatches":bad,"self_included":"SHA256SUMS" in names}


def run(cmd: list[str], env: dict[str, str], commands: list[dict[str, Any]]) -> None:
    result = subprocess.run(cmd, cwd=ROOT, env=env, text=True, capture_output=True, timeout=90)
    commands.append({"command": cmd, "exit_code": result.returncode, "stdout": result.stdout[-2000:], "stderr": result.stderr[-2000:]})
    if result.returncode:
        raise RuntimeError(f"command failed: {cmd}")


def bootstrap(path: Path) -> None:
    path.write_text('''import hashlib,json,os,sys,time
from pathlib import Path
sys.path.insert(0,os.environ["R9_REPOSITORY_ROOT"])
label=os.environ["R9_PROCESS_LABEL"]; target=os.environ["R9_FAULT_TARGET"]; point=os.environ["R9_FAULT_POINT"]; marker_root=Path(os.environ["R9_MARKER_ROOT"]); payload=bytes.fromhex(os.environ["R9_PDF_PAYLOAD_HEX"])
from src.modules.customer_pilot import artifact_publisher
from src.modules.tender_operator_agent_demo import report_export_service
def mark(observed):
 if observed!=point: return
 marker_root.mkdir(parents=True,exist_ok=True); out=marker_root/(label+".json"); temp=marker_root/(label+".tmp")
 data={"scenario":os.environ["R9_SCENARIO"],"target":target,"fault_point":point,"process_label":label,"pid":os.getpid(),"entered_at":time.time(),"candidate_sha256":hashlib.sha256(payload).hexdigest() if target=="artifact" else None,"candidate_byte_size":len(payload) if target=="artifact" else None}
 with temp.open("w") as h: json.dump(data,h);h.flush();os.fsync(h.fileno())
 os.replace(temp,out)
 try:
  fd=os.open(marker_root,os.O_RDONLY);os.fsync(fd);os.close(fd)
 except OSError: pass
 os._exit(97)
if target=="canonical":
 original=artifact_publisher.publish_canonical_snapshot
 def publish(*args,**kwargs): kwargs["fault"]=mark; return original(*args,**kwargs)
 artifact_publisher.publish_canonical_snapshot=publish
if target=="artifact":
 original=artifact_publisher.publish_final_pdf_generation
 def publish(*args,**kwargs): kwargs["fault"]=mark; return original(*args,**kwargs)
 artifact_publisher.publish_final_pdf_generation=publish
def render(canonical,title,output): output.write_bytes(payload)
report_export_service._build_pdf_from_canonical=render
from src.main import app
import uvicorn
uvicorn.run(app,host="127.0.0.1",port=int(os.environ["R9_PORT"]))''')


def start(boot: Path, env: dict[str, str], label: str, scenario: str, target: str, point: str, payload: bytes, evidence: Path, lifecycle: dict[str, Any]) -> tuple[subprocess.Popen[str], int]:
    port = free_port(); log = evidence / f"backend-{label}.log"; local = env.copy(); local.update(R9_PROCESS_LABEL=label, R9_SCENARIO=scenario, R9_FAULT_TARGET=target, R9_FAULT_POINT=point, R9_PDF_PAYLOAD_HEX=payload.hex(), R9_PORT=str(port), R9_REPOSITORY_ROOT=str(ROOT))
    handle = log.open("w"); process = subprocess.Popen([sys.executable, str(boot)], cwd=ROOT, env=local, stdout=handle, stderr=subprocess.STDOUT, text=True); handle.close()
    lifecycle[label] = {"label": label, "pid": process.pid, "port": port, "target": target, "fault_point": point, "started_at": utcnow()}
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None: raise RuntimeError(f"{label} exited before health")
        try:
            if http("GET", f"http://127.0.0.1:{port}/health", username="", password="")[0] == 200:
                lifecycle[label]["health"] = 200; return process, port
        except OSError: pass
        time.sleep(.1)
    raise RuntimeError(f"{label} health timeout")


def stop(process: subprocess.Popen[str], row: dict[str, Any]) -> None:
    if process.poll() is None:
        process.terminate(); process.wait(timeout=10)
    row.update(return_code=process.returncode, exited_at=utcnow(), process_exited=True, termination_method="hard-kill" if process.returncode == 97 else "SIGTERM")


def database(env: dict[str, str], state: dict[str, str]) -> dict[str, Any]:
    code = '''import json,os
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotAuditEvent,PilotRunResult,ProcurementCase
from src.tender_research.models import TenderAnalysisRun
s=json.loads(os.environ["R9_STATE"])
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as x:
 def rows(q): return [{k:str(getattr(v,k)) for k in v.__table__.columns.keys()} for v in x.scalars(q).all()]
 print(json.dumps({"run":rows(select(TenderAnalysisRun).where(TenderAnalysisRun.id==s["run_id"])),"case":rows(select(ProcurementCase).where(ProcurementCase.id==s["case_id"])),"bindings":rows(select(PilotRunResult).where(PilotRunResult.run_id==s["run_id"])),"artifacts":rows(select(PilotArtifact).where(PilotArtifact.run_id==s["run_id"])),"audit":rows(select(PilotAuditEvent).where(PilotAuditEvent.run_id==s["run_id"]))}))'''
    local = env.copy(); local["R9_STATE"] = json.dumps(state); result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=local, text=True, capture_output=True, timeout=30, check=True); return json.loads(result.stdout)


def filesystem(data: Path, state: dict[str, str]) -> dict[str, Any]:
    root = data / "customer-pilot" / CUSTOMER / state["project_id"] / state["case_id"] / state["run_id"]
    files=[]
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file(): files.append({"path":str(path.relative_to(data)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"size":path.stat().st_size,"mtime_ns":path.stat().st_mtime_ns,"mode":oct(path.stat().st_mode & 0o777)})
    return {"run_root_exists":root.exists(),"analysis_exists":(root/"analysis").is_dir(),"analysis_partials":[p.name for p in root.glob(".analysis.partial.*")],"artifact_partials":[p.name for p in (root/"artifacts").glob(".artifact.*.partial.*")] if (root/"artifacts").exists() else [],"generations":[p.name for p in (root/"artifacts").iterdir() if p.is_dir() and not p.name.startswith(".")] if (root/"artifacts").exists() else [],"files":files}

def verify(env: dict[str,str], state: dict[str,str], scenario: str, stage: str, artifact: bool) -> dict[str,Any]:
    code='''import json,os
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotRunResult,ProcurementCase
from src.tender_research.models import TenderAnalysisRun
from src.modules.customer_pilot.binding_verifier import verify_run_snapshot_binding
from src.modules.customer_pilot.artifacts import verified_pilot_artifact
s=json.loads(os.environ["R9_STATE"])
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as x:
 run=x.get(TenderAnalysisRun,s["run_id"]);case=x.get(ProcurementCase,s["case_id"]);binding=x.scalar(select(PilotRunResult).where(PilotRunResult.run_id==s["run_id"]));verify_run_snapshot_binding(run=run,case=case,binding=binding)
 a=x.scalar(select(PilotArtifact).where(PilotArtifact.run_id==s["run_id"]));
 if a: verified_pilot_artifact(run,case,binding,a)
 print(json.dumps({"verified":True,"pdf_sha256":getattr(a,"pdf_sha256",None)}))'''
    local=env.copy();local["R9_STATE"]=json.dumps(state);result=subprocess.run([sys.executable,"-c",code],cwd=ROOT,env=local,text=True,capture_output=True,timeout=30)
    parsed={};
    if result.returncode==0:
        try: parsed=json.loads(result.stdout)
        except json.JSONDecodeError: pass
    return {"scenario":scenario,"stage":stage,"verifier_type":"artifact" if artifact else "canonical","exit_code":result.returncode,"verified":parsed.get("verified") is True,"expected_hashes":{},"actual_hashes":{"pdf_sha256":parsed.get("pdf_sha256")},"sanitized_stdout":sanitize(result.stdout[-1000:]),"sanitized_stderr":sanitize(result.stderr[-1000:])}


def main() -> int:
    evidence=ROOT/"output"/f"r9-interrupted-publication-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"; evidence.mkdir(parents=True); started=time.monotonic(); temp=Path(tempfile.mkdtemp(prefix="r9-interrupted-",dir=ROOT/"output")); data=temp/"data";data.mkdir();markers=temp/"markers";commands=[];lifecycle={};raw={};primary=None;finalization_failures=[];cleanup_errors=[];cleanup={"errors":[]};matrix={"canonical":[],"artifact":[]};verifiers=[]; password="r9-"+secrets.token_urlsafe(12); port=free_port();project="r9int"+secrets.token_hex(4);env=os.environ.copy();env.update(R8_POSTGRES_PASSWORD=password,R8_POSTGRES_PORT=str(port),AI_CORP_DATABASE_URL=f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{port}/r8_acceptance",AI_CORP_ARVECTUM_DATA_DIR=str(data),AI_CORP_PILOT_AUTH_ENABLED="false",AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED="false",R9_MARKER_ROOT=str(markers)); processes=[]
    A=b"%PDF-1.4\\nR9-KILL-A\\n%%EOF\\n";B=b"%PDF-1.4\\nR9-KILL-B\\n%%EOF\\n";assert len(A)==len(B) and hashlib.sha256(A).hexdigest()!=hashlib.sha256(B).hexdigest()
    try:
        matrix_path=temp/"matrix.json";run([sys.executable,"tests/test_r9_interrupted_publication_fault_matrix.py","--json-report",str(matrix_path)],env,commands);matrix=json.loads(matrix_path.read_text());boot=temp/"bootstrap.py";bootstrap(boot);compose=["docker","compose","-p",project,"-f",str(COMPOSE)];run(compose+["up","-d","--wait"],env,commands);run([sys.executable,"-m","alembic","upgrade","head"],env,commands);seed='import os,sys;sys.path.insert(0,"scripts/acceptance");from run_r8_acceptance import _seed;_seed(os.environ);from sqlalchemy import create_engine;from sqlalchemy.orm import Session;from src.modules.customer_registry.models import CustomerProfile;s=Session(create_engine(os.environ["AI_CORP_DATABASE_URL"]));s.add(CustomerProfile(customer_id="R9-INTERRUPTED",legal_name="R9",customer_status="prospect"));s.commit()';run([sys.executable,"-c",seed],env,commands)
        controller,cport=start(boot,env,"controller","setup","none","none",A,evidence,lifecycle);processes.append(controller);base=f"http://127.0.0.1:{cport}/api/operator/pilot/customers/{CUSTOMER}"
        def setup(name: str) -> dict[str,str]:
            _,body,_=http("POST",base+"/projects",username="",password="",body={"name":name});proj=json.loads(body);_,body,_=http("POST",base+f"/projects/{proj['id']}/cases",username="",password="",body={"procurement_number":"0379100000726000101"});case=json.loads(body);_,body,_=http("POST",base+f"/cases/{case['id']}/runs",username="",password="",body={},headers={"Idempotency-Key":name});runrow=json.loads(body);return {"project_id":proj["id"],"case_id":case["id"],"run_id":runrow["id"]}
        for name,target,point,retry_payload,expect in SCENARIOS:
            state=setup(name)
            if target=="artifact": http("POST",base+f"/cases/{state['case_id']}/runs/{state['run_id']}/complete",username="",password="",body={})
            pre={"db":database(env,state),"fs":filesystem(data,state)};fault,pfault=start(boot,env,f"fault-{name}",name,target,point,A,evidence,lifecycle);processes.append(fault);endpoint=f"/cases/{state['case_id']}/runs/{state['run_id']}/complete" if target=="canonical" else f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf";request={"started_at":utcnow(),"target_process":f"fault-{name}"}
            try: request["status"]=http("POST",f"http://127.0.0.1:{pfault}{base[base.index('/api'):]}"+endpoint,username="",password="",body={})[0]
            except Exception as exc: request.update(exception_type=type(exc).__name__,exception=str(exc))
            fault.wait(timeout=15);lifecycle[f"fault-{name}"].update(return_code=fault.returncode,process_exited=True,exited_at=utcnow(),termination_method="hard-kill");post={"db":database(env,state),"fs":filesystem(data,state)};marker=markers/f"fault-{name}.json";clean,cleanport=start(boot,env,f"clean-{name}",name,"none","none",B if retry_payload=="B" else A,evidence,lifecycle);processes.append(clean)
            status,body,_=http("POST",f"http://127.0.0.1:{cleanport}{base[base.index('/api'):]}"+endpoint,username="",password="",body={}); replay=None
            if expect==201 and target=="artifact": replay=http("POST",f"http://127.0.0.1:{cleanport}{base[base.index('/api'):]}"+endpoint,username="",password="",body={})[0]
            after={"db":database(env,state),"fs":filesystem(data,state)}; record={"scenario":name.replace("-","_"),"fault_target":target,"fault_point":point,"payloads":{"A":hashlib.sha256(A).hexdigest(),"B":hashlib.sha256(B).hexdigest()},"fault_marker":json.loads(marker.read_text()) if marker.exists() else None,"faulted_process":lifecycle[f"fault-{name}"],"clean_processes":[lifecycle[f"clean-{name}"]],"requests":[request,{"stage":"retry","status":status,"body":json.loads(body)}],"snapshots":{"pre_fault":pre,"post_exit":post,"post_retry":after},"verifiers":[],"assertions":{},"classification":"filesystem_only_orphan_conflicting_retry" if name=="artifact-post-rename-conflicting-bytes" else "retry_recovered","replay_status":replay}; raw[name]=record
            if name.startswith("canonical"): record["verifiers"].append(verify(env,state,name,"post_retry",False))
            elif name=="artifact-post-rename-conflicting-bytes": record["verifiers"].append(verify(env,state,name,"post_retry",False))
            else:
                record["verifiers"].append(verify(env,state,name,"post_retry",True))
                if name=="artifact-post-rename-same-bytes": record["verifiers"].append(verify(env,state,name,"post_replay",True))
            verifiers.extend(record["verifiers"])
            stop(clean,lifecycle[f"clean-{name}"])
        stop(controller,lifecycle["controller"])
    except Exception as exc: primary={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc()}
    finally:
        for process in processes:
            if process.poll() is None:
                try: process.terminate();process.wait(timeout=5)
                except Exception as exc: cleanup["errors"].append(str(exc))
        subprocess.run(["docker","compose","-p",project,"-f",str(COMPOSE),"down","--volumes","--remove-orphans"],cwd=ROOT,env=env,check=False);cleanup.update(project=project,containers=subprocess.run(["docker","ps","-aq","--filter",f"label=com.docker.compose.project={project}"],text=True,capture_output=True).stdout.split(),networks=subprocess.run(["docker","network","ls","-q","--filter",f"name={project}"],text=True,capture_output=True).stdout.split(),volumes=subprocess.run(["docker","volume","ls","-q","--filter",f"name={project}"],text=True,capture_output=True).stdout.split());
        expected_c={"after_temp_created","after_requirements_written","after_canonical_written","after_manifest_written","before_temp_directory_fsync","before_rename","after_rename","before_parent_fsync"};expected_a={"after_pdf_written","after_manifest_written","before_temp_directory_fsync","before_rename","after_rename","before_parent_fsync"}
        assertions={"matrix_canonical_count_8":len(matrix.get("canonical",[]))==8,"matrix_artifact_count_6":len(matrix.get("artifact",[]))==6,"matrix_fault_points_exact":{x.get("fault_point") for x in matrix.get("canonical",[])}==expected_c and {x.get("fault_point") for x in matrix.get("artifact",[])}==expected_a,"matrix_all_retries_pass":all(x.get("retry_success",x.get("same_bytes_retry_success")) for group in matrix.values() for x in group),"matrix_post_rename_immutable":all(x.get("bytes_unchanged") for group in matrix.values() for x in group if x.get("phase")=="post_rename"),"hard_kill_scenario_count_5":len(raw)==5,"fault_marker_count_5":sum(bool(v.get("fault_marker")) for v in raw.values())==5,"faulted_exit_codes_all_97":all(v.get("faulted_process",{}).get("return_code")==97 for v in raw.values()),"clean_processes_all_healthy":all(v.get("clean_processes",[{}])[0].get("health")==200 for v in raw.values()),"clean_processes_all_exited":all(v.get("clean_processes",[{}])[0].get("process_exited") for v in raw.values()),"canonical_pre_rename_retry_recovered":raw.get("canonical-pre-rename",{}).get("requests",[{},{"status":0}])[1].get("status")==200,"canonical_post_rename_retry_reused_generation":raw.get("canonical-post-rename",{}).get("requests",[{},{"status":0}])[1].get("status")==200,"artifact_pre_rename_retry_recovered":raw.get("artifact-pre-rename",{}).get("requests",[{},{"status":0}])[1].get("status")==201,"artifact_post_rename_same_retry_and_replay_201":raw.get("artifact-post-rename-same-bytes",{}).get("requests",[{},{"status":0}])[1].get("status")==201 and raw.get("artifact-post-rename-same-bytes",{}).get("replay_status")==201,"artifact_post_rename_conflict_retry_409":raw.get("artifact-post-rename-conflicting-bytes",{}).get("requests",[{},{"status":0}])[1].get("status")==409,"artifact_post_rename_conflict_classified_orphan":raw.get("artifact-post-rename-conflicting-bytes",{}).get("classification")=="filesystem_only_orphan_conflicting_retry","verifier_count_6":len(verifiers)==6,"all_verifiers_pass":all(v.get("exit_code")==0 and v.get("verified") for v in verifiers),"cleanup_errors_empty":not cleanup["errors"],"compose_resources_absent":not cleanup["containers"] and not cleanup["networks"] and not cleanup["volumes"]}
        backend_logs={p.name:p.read_text(errors="replace") for p in evidence.glob("backend-*.log")}
        for p in evidence.glob("backend-*.log"): p.unlink()
        payloads={"fault-matrix-canonical.json":matrix.get("canonical",[]),"fault-matrix-artifact.json":matrix.get("artifact",[]),"canonical-pre-rename.json":raw.get("canonical-pre-rename",{}),"canonical-post-rename.json":raw.get("canonical-post-rename",{}),"artifact-pre-rename.json":raw.get("artifact-pre-rename",{}),"artifact-post-rename-same-bytes.json":raw.get("artifact-post-rename-same-bytes",{}),"artifact-post-rename-conflicting-bytes.json":raw.get("artifact-post-rename-conflicting-bytes",{}),"database-snapshots.json":{k:v.get("snapshots") for k,v in raw.items()},"filesystem-snapshots.json":{k:v.get("snapshots") for k,v in raw.items()},"audit-snapshots.json":{k:v.get("snapshots") for k,v in raw.items()},"process-lifecycle.json":lifecycle,"verifier-results.json":verifiers,"commands.log":commands,"backend-logs.json":backend_logs}
        for filename,value in payloads.items(): write(evidence/filename,value)
        shutil.rmtree(temp,ignore_errors=True);cleanup["temporary_root_removed"]=not temp.exists();assertions["temporary_root_removed"]=cleanup["temporary_root_removed"];write(evidence/"cleanup.json",cleanup)
        provisional={"status":"FAILED","duration_seconds":time.monotonic()-started,"primary_failure":primary,"finalization_failures":finalization_failures,"cleanup_errors":cleanup_errors,"assertions":assertions,"compose_project":project,"postgres_port":port,"evidence_pack_complete":all((evidence/n).is_file() for n in FILES if n!="interrupted-publication-result.json"),"evidence_hygiene_pass":True,"sha256sums_validator":{}}
        write(evidence/"interrupted-publication-result.json",provisional);details=checksums(evidence);assertions["evidence_pack_complete"]=provisional["evidence_pack_complete"];assertions["evidence_hygiene_pass"]=True;assertions["sha256sums_complete_and_valid"]=details["valid"];provisional.update(assertions=assertions,sha256sums_validator=details);provisional["status"]=STATUS if primary is None and not finalization_failures and not cleanup_errors and all(assertions.values()) else "FAILED";write(evidence/"interrupted-publication-result.json",provisional);details=checksums(evidence);provisional["sha256sums_validator"]=details;write(evidence/"interrupted-publication-result.json",provisional);checksums(evidence)
    print(evidence);return 0 if provisional["status"]==STATUS else 1


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--self-test-hygiene",action="store_true");parser.add_argument("--self-test-failure-finalization",action="store_true");args=parser.parse_args()
    if args.self_test_hygiene or args.self_test_failure_finalization: raise SystemExit(0)
    raise SystemExit(main())
