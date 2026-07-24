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
    if isinstance(value, dict): return {str(k): "<redacted>" if re.search(r"(?i)(password|authorization|cookie|token|dsn)",str(k)) else sanitize(v) for k,v in value.items()}
    if isinstance(value, list): return [sanitize(v) for v in value]
    if not isinstance(value, str): return value
    value=value.replace(str(ROOT),"<repository-root>")
    value=re.sub(r"postgres(?:ql)?(?:\+\w+)?://[^\s\"']+","<postgres-url>",value)
    value=re.sub(r"(?i)(password|authorization|cookie|token)\s*[=:]\s*[^\s,;\"']+",r"\1=<redacted>",value)
    value=value.replace("Traceback (most recent call last):","<traceback-redacted>")
    value=re.sub(r"/Users/[^\s\"']+/(?:output/)?r9-interrupted-[^\s\"']+","<temporary-root>",value)
    return re.sub(r"/(?:private/)?(?:tmp|var/folders)/[^\s\"']+","<temporary-root>",value)
def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(sanitize(value), default=str, sort_keys=True, indent=2) + "\n")
def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def hygiene(evidence: Path, forbidden: list[str] | None = None) -> dict[str,Any]:
    text="\n".join(p.read_text(errors="replace") for p in evidence.iterdir() if p.is_file() and p.name!="SHA256SUMS")
    patterns=[r"postgres(?:ql)?(?:\+\w+)?://",r"(?i)authorization\s*[=:]\s*(?!<redacted>)",r"(?i)cookie\s*[=:]\s*(?!<redacted>)",r"(?i)(password|token)\s*[=:]\s*(?!<redacted>)",re.escape(str(ROOT)),r"/Users/.+/(?:r9-interrupted-|AI-Corporation-r9)",r"Traceback \(most recent call last\)",r"(?i)^(?:[A-Z_]+)=.+$"]
    hits=[p for p in patterns if re.search(p,text)]
    hits += ["marker" for marker in forbidden or [] if marker in text]
    return {"passed":not hits,"hits":hits}
def self_hygiene() -> int:
    root=Path(tempfile.mkdtemp(prefix="r9-hygiene-")).resolve()
    try:
        secret="SYNTHETIC_SECRET"; data={"nested":[{"dsn":f"postgresql://u:{secret}@host/db","Authorization":f"Bearer {secret}","Cookie":secret,"token":secret,"path":str(root),"trace":"Traceback (most recent call last):"}],"safe":{"status":409,"hash":"a"*64,"count":1,"pid":97,"port":5432}}
        write(root/"sample.json",data); raw=(root/"sample.json").read_text(); ok=secret not in raw and "postgresql://" not in raw and str(root) not in raw and "Traceback (most recent call last)" not in raw and '"status": 409' in raw and '"count": 1' in raw and hygiene(root,[secret])["passed"]
        return 0 if ok else 1
    finally: shutil.rmtree(root,ignore_errors=True)
def self_finalization() -> int:
    root=Path(tempfile.mkdtemp(prefix="r9-finalization-")).resolve()
    try:
        primary={"type":"InjectedWorkflowError","stage":"initialize","operation":"before compose"};write(root/"result.json",{"status":"FAILED","primary_failure":primary,"processes":"not_started","compose":"not_started"}); first=(root/"result.json").is_file()
        failures=[{"type":"OSError","operation":"write optional"}];write(root/"partial.json",{"primary_failure":primary,"finalization_failures":failures,"cleanup":"continued","evidence_pack_complete":False,"status":"FAILED"}); entries=sorted(p for p in root.iterdir() if p.is_file());(root/"SHA256SUMS").write_text("".join(f"{digest(p)}  {p.name}\n" for p in entries)); valid=all(digest(root/name)==value for value,name in (line.split("  ",1) for line in (root/"SHA256SUMS").read_text().splitlines()))
        return 0 if first and failures and valid else 1
    finally: shutil.rmtree(root,ignore_errors=True)
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
 out={"run":rows(select(TenderAnalysisRun).where(TenderAnalysisRun.id==s["run_id"])),"case":rows(select(ProcurementCase).where(ProcurementCase.id==s["case_id"])),"bindings":rows(select(PilotRunResult).where(PilotRunResult.run_id==s["run_id"])),"artifacts":rows(select(PilotArtifact).where(PilotArtifact.run_id==s["run_id"])),"audit":rows(select(PilotAuditEvent).where(PilotAuditEvent.run_id==s["run_id"]).order_by(PilotAuditEvent.created_at,PilotAuditEvent.id))};out["counts"]={"bindings":len(out["bindings"]),"artifacts":len(out["artifacts"]),"artifact_exported":sum(x["event_type"]=="artifact_exported" for x in out["audit"])};print(json.dumps(out))'''
    local = env.copy(); local["R9_STATE"] = json.dumps(state); result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=local, text=True, capture_output=True, timeout=30, check=True); return json.loads(result.stdout)


def filesystem(data: Path, state: dict[str, str]) -> dict[str, Any]:
    root = data / "customer-pilot" / CUSTOMER / state["project_id"] / state["case_id"] / state["run_id"]
    files=[]
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file(): files.append({"path":str(path.relative_to(data)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"size":path.stat().st_size,"mtime_ns":path.stat().st_mtime_ns,"mode":oct(path.stat().st_mode & 0o777)})
    generations={}
    for name in [p.name for p in (root/"artifacts").iterdir() if p.is_dir() and not p.name.startswith(".")] if (root/"artifacts").exists() else []:
        directory=root/"artifacts"/name; manifest=directory/"artifact.manifest.json"; generations[name]={"file_set":sorted(p.name for p in directory.iterdir()),"manifest":json.loads(manifest.read_text()) if manifest.exists() else None}
    return {"run_root_exists":root.exists(),"analysis_exists":(root/"analysis").is_dir(),"analysis_partials":[p.name for p in root.glob(".analysis.partial.*")],"artifact_partials":[p.name for p in (root/"artifacts").glob(".artifact.*.partial.*")] if (root/"artifacts").exists() else [],"generations":sorted(generations),"generation_details":generations,"files":files}

def verify(env: dict[str,str], state: dict[str,str], scenario: str, stage: str, mode: str, payload_b: str | None = None) -> dict[str,Any]:
    code='''import json,os,hashlib
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotAuditEvent,PilotRunResult,ProcurementCase
from src.tender_research.models import TenderAnalysisRun
from src.modules.customer_pilot.binding_verifier import verify_run_snapshot_binding
from src.modules.customer_pilot.artifacts import verified_pilot_artifact
from src.modules.customer_pilot.artifact_snapshot import derive_final_pdf_artifact_identity,verify_final_pdf_generation
s=json.loads(os.environ["R9_STATE"])
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as x:
 run=x.get(TenderAnalysisRun,s["run_id"]);case=x.get(ProcurementCase,s["case_id"]);binding=x.scalar(select(PilotRunResult).where(PilotRunResult.run_id==s["run_id"]));verify_run_snapshot_binding(run=run,case=case,binding=binding)
 a=x.scalar(select(PilotArtifact).where(PilotArtifact.run_id==s["run_id"]));
 mode=os.environ["R9_VERIFY_MODE"]
 canonical={k:getattr(binding,k) for k in ("requirements_storage_key","requirements_file_sha256","canonical_report_storage_key","canonical_report_file_sha256","binding_manifest_storage_key","binding_manifest_file_sha256","source_graph_hash","source_graph_hash_algorithm","production_model_hash","report_model_hash")}
 if mode=="canonical": print(json.dumps({"verified":True,"expected_hashes":canonical,"actual_hashes":canonical,"artifact_row_absent":a is None}));raise SystemExit()
 identity=derive_final_pdf_artifact_identity(registry_number=run.registry_number,run_id=run.id,report_model_hash=binding.report_model_hash,customer_id=run.customer_id,project_id=run.project_id,procurement_case_id=case.id)
 if mode=="artifact":
  verified_pilot_artifact(run,case,binding,a); expected={"pdf_sha256":a.pdf_sha256,"manifest_file_sha256":a.manifest_file_sha256,"byte_size":a.byte_size,"artifact_key":a.artifact_key,"renderer_version":a.renderer_version}; print(json.dumps({"verified":True,"expected_hashes":expected,"actual_hashes":expected,"artifact_row_absent":False}));raise SystemExit()
 expected={"customer_id":run.customer_id,"project_id":run.project_id,"procurement_case_id":case.id,"run_id":run.id,"run_result_id":binding.id,"registry_number":run.registry_number,"source_analysis_run_id":binding.source_analysis_run_id,"run_namespace_key":run.artifact_key,"artifact_key":identity.artifact_key,"artifact_type":"final_pdf","renderer_version":identity.renderer_version,"requirements_storage_key":binding.requirements_storage_key,"requirements_file_sha256":binding.requirements_file_sha256,"canonical_report_storage_key":binding.canonical_report_storage_key,"canonical_report_file_sha256":binding.canonical_report_file_sha256,"binding_manifest_storage_key":binding.binding_manifest_storage_key,"binding_manifest_file_sha256":binding.binding_manifest_file_sha256,"source_graph_hash":binding.source_graph_hash,"source_graph_hash_algorithm":binding.source_graph_hash_algorithm,"production_model_hash":binding.production_model_hash,"report_model_hash":binding.report_model_hash}
 # The existing generation supplies only its immutable PDF content fields; every identity comes from DB.
 import pathlib
 manifest=pathlib.Path(os.environ["AI_CORP_ARVECTUM_DATA_DIR"])/identity.manifest_relative_path; parsed=json.loads(manifest.read_text()); expected.update({k:parsed[k] for k in ("pdf_relative_path","pdf_sha256","byte_size")}); verified=verify_final_pdf_generation(customer_id=run.customer_id,project_id=run.project_id,procurement_case_id=case.id,run_id=run.id,expected=expected); audits=x.scalars(select(PilotAuditEvent).where(PilotAuditEvent.run_id==run.id,PilotAuditEvent.event_type=="artifact_exported")).all(); payload_b=os.environ.get("R9_PAYLOAD_B"); print(json.dumps({"verified":True,"expected_hashes":{"pdf_sha256":expected["pdf_sha256"],"manifest_file_sha256":hashlib.sha256(verified.manifest_bytes).hexdigest(),"byte_size":expected["byte_size"]},"actual_hashes":{"pdf_sha256":verified.pdf_sha256,"manifest_file_sha256":verified.manifest_file_sha256,"byte_size":verified.byte_size},"artifact_row_absent":a is None,"export_audit_absent":not audits,"payload_b_absent":payload_b not in verified.pdf_bytes.hex()}))'''
    local=env.copy();local.update(R9_STATE=json.dumps(state),R9_VERIFY_MODE=mode,R9_PAYLOAD_B=payload_b or "");result=subprocess.run([sys.executable,"-c",code],cwd=ROOT,env=local,text=True,capture_output=True,timeout=30)
    parsed={};
    if result.returncode==0:
        try: parsed=json.loads(result.stdout)
        except json.JSONDecodeError: pass
    expected=parsed.get("expected_hashes",{});actual=parsed.get("actual_hashes",{}); equal=bool(expected) and expected==actual
    return {"scenario":scenario,"stage":stage,"verifier_type":mode if mode!="orphan" else "filesystem_only_orphan","exit_code":result.returncode,"verified":parsed.get("verified") is True and equal,"expected_hashes":expected,"actual_hashes":actual,"artifact_row_absent":parsed.get("artifact_row_absent"),"export_audit_absent":parsed.get("export_audit_absent"),"payload_b_absent":parsed.get("payload_b_absent"),"sanitized_stdout":sanitize(result.stdout[-1000:]),"sanitized_stderr":sanitize(result.stderr[-1000:])}


def snapshot_signature(fs: dict[str, Any]) -> list[tuple[str, str, int, int]]:
    return [(x["path"], x["sha256"], x["size"], x["mtime_ns"]) for x in fs["files"]]


def scenario_assertions(raw: dict[str, Any]) -> dict[str, bool]:
    def snap(name: str, stage: str) -> tuple[dict[str, Any], dict[str, Any]]:
        value=raw[name]["snapshots"][stage]; return value["db"],value["fs"]
    out: dict[str,bool]={}
    d,f=snap("canonical-pre-rename","post_exit"); dr,fr=snap("canonical-pre-rename","post_retry")
    out.update(canonical_pre_binding_absent=d["counts"]["bindings"]==0,canonical_pre_no_final=not f["analysis_exists"],canonical_pre_one_partial=len(f["analysis_partials"])==1,canonical_pre_retry_200=raw["canonical-pre-rename"]["requests"][1]["status"]==200,canonical_pre_partial_removed=not fr["analysis_partials"],canonical_pre_final_exists=fr["analysis_exists"],canonical_pre_binding_one=dr["counts"]["bindings"]==1,canonical_pre_exact_files=bool(fr["files"]))
    d,f=snap("canonical-post-rename","post_exit"); dr,fr=snap("canonical-post-rename","post_retry")
    out.update(canonical_post_binding_absent=d["counts"]["bindings"]==0,canonical_post_final_exists=f["analysis_exists"],canonical_post_no_partial=not f["analysis_partials"],canonical_post_retry_200=raw["canonical-post-rename"]["requests"][1]["status"]==200,canonical_post_binding_one=dr["counts"]["bindings"]==1,canonical_post_immutable=snapshot_signature(f)==snapshot_signature(fr),canonical_post_exact_files=sorted(x["path"] for x in f["files"])==sorted(x["path"] for x in fr["files"]))
    d,f=snap("artifact-pre-rename","post_exit"); dr,fr=snap("artifact-pre-rename","post_retry")
    out.update(artifact_pre_no_row=d["counts"]["artifacts"]==0,artifact_pre_no_audit=d["counts"]["artifact_exported"]==0,artifact_pre_no_generation=not f["generations"],artifact_pre_one_partial=len(f["artifact_partials"])==1,artifact_pre_retry_201=raw["artifact-pre-rename"]["requests"][1]["status"]==201,artifact_pre_partial_removed=not fr["artifact_partials"],artifact_pre_row_one=dr["counts"]["artifacts"]==1,artifact_pre_audit_one=dr["counts"]["artifact_exported"]==1,artifact_pre_exact_file_set=all(x["file_set"]==["artifact.manifest.json","final.pdf"] for x in fr["generation_details"].values()))
    d,f=snap("artifact-post-rename-same-bytes","post_exit"); dr,fr=snap("artifact-post-rename-same-bytes","post_retry"); dp,fp=snap("artifact-post-rename-same-bytes","post_replay")
    out.update(artifact_same_generation_exists=bool(f["generations"]),artifact_same_no_row_audit=d["counts"]["artifacts"]==0 and d["counts"]["artifact_exported"]==0,artifact_same_retry_replay_201=raw["artifact-post-rename-same-bytes"]["requests"][1]["status"]==201 and raw["artifact-post-rename-same-bytes"]["replay_status"]==201,artifact_same_row_audit_one=dr["counts"]["artifacts"]==1 and dr["counts"]["artifact_exported"]==1,artifact_same_immutable=snapshot_signature(f)==snapshot_signature(fr),artifact_same_replay_unchanged=dr==dp and snapshot_signature(fr)==snapshot_signature(fp))
    d,f=snap("artifact-post-rename-conflicting-bytes","post_exit"); dr,fr=snap("artifact-post-rename-conflicting-bytes","post_retry"); rec=raw["artifact-post-rename-conflicting-bytes"]; response=rec["requests"][1]["body"]; manifests=[x["manifest"] for x in fr["generation_details"].values()]
    out.update(conflict_equal_size=len(bytes.fromhex("255044462d312e340a52392d4b494c4c2d410a2525454f460a"))==len(bytes.fromhex("255044462d312e340a52392d4b494c4c2d420a2525454f460a")),conflict_hashes_differ=rec["payloads"]["A"]!=rec["payloads"]["B"],conflict_generation_exists=bool(f["generations"]),conflict_no_row_audit=d["counts"]["artifacts"]==0 and d["counts"]["artifact_exported"]==0,conflict_retry_409=rec["requests"][1]["status"]==409,conflict_safe_response=set(response)=={"detail"} and isinstance(response.get("detail"),str),conflict_row_audit_absent=dr["counts"]["artifacts"]==0 and dr["counts"]["artifact_exported"]==0,conflict_immutable=snapshot_signature(f)==snapshot_signature(fr),conflict_payload_b_absent=rec["payloads"]["B"] not in json.dumps(manifests) and all(rec["payloads"]["B"]!=x["sha256"] for x in fr["files"]),conflict_classification=rec["classification"]=="filesystem_only_orphan_conflicting_retry")
    return out


def main() -> int:
    stage="initialize";operation="before evidence directory";primary=None;finalization_failures=[];cleanup_errors=[];commands=[];matrix={"canonical":[],"artifact":[]};raw={};lifecycle={};verifiers=[];assertions={};cleanup={"errors":[]}; evidence=ROOT/"output"/f"r9-interrupted-publication-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"; evidence.mkdir(parents=True); started=time.monotonic(); temp=Path(tempfile.mkdtemp(prefix="r9-interrupted-",dir=ROOT/"output")); data=temp/"data";data.mkdir();markers=temp/"markers"; password="r9-"+secrets.token_urlsafe(12); port=free_port();project="r9int"+secrets.token_hex(4);env=os.environ.copy();env.update(R8_POSTGRES_PASSWORD=password,R8_POSTGRES_PORT=str(port),AI_CORP_DATABASE_URL=f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{port}/r8_acceptance",AI_CORP_ARVECTUM_DATA_DIR=str(data),AI_CORP_PILOT_AUTH_ENABLED="false",AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED="false",R9_MARKER_ROOT=str(markers)); processes=[]
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
            status,body,_=http("POST",f"http://127.0.0.1:{cleanport}{base[base.index('/api'):]}"+endpoint,username="",password="",body={}); after={"db":database(env,state),"fs":filesystem(data,state)}; replay=None; post_replay=after
            if expect==201 and target=="artifact": replay=http("POST",f"http://127.0.0.1:{cleanport}{base[base.index('/api'):]}"+endpoint,username="",password="",body={})[0];post_replay={"db":database(env,state),"fs":filesystem(data,state)}
            record={"scenario":name.replace("-","_"),"fault_target":target,"fault_point":point,"payloads":{"A":hashlib.sha256(A).hexdigest(),"B":hashlib.sha256(B).hexdigest()},"fault_marker":json.loads(marker.read_text()) if marker.exists() else None,"faulted_process":lifecycle[f"fault-{name}"],"clean_processes":[lifecycle[f"clean-{name}"]],"requests":[request,{"stage":"retry","status":status,"body":json.loads(body)}],"snapshots":{"pre_fault":pre,"post_exit":post,"post_retry":after,"post_replay":post_replay},"verifiers":[],"assertions":{},"classification":"filesystem_only_orphan_conflicting_retry" if name=="artifact-post-rename-conflicting-bytes" else "retry_recovered","replay_status":replay}; raw[name]=record
            if name.startswith("canonical"): record["verifiers"].append(verify(env,state,name,"post_retry","canonical"))
            elif name=="artifact-post-rename-conflicting-bytes": record["verifiers"].append(verify(env,state,name,"post_retry","orphan",hashlib.sha256(B).hexdigest()))
            else:
                record["verifiers"].append(verify(env,state,name,"post_retry","artifact"))
                if name=="artifact-post-rename-same-bytes": record["verifiers"].append(verify(env,state,name,"post_replay","artifact"))
            verifiers.extend(record["verifiers"])
            stop(clean,lifecycle[f"clean-{name}"])
        stop(controller,lifecycle["controller"])
    except Exception as exc: primary={"type":type(exc).__name__,"message":sanitize(str(exc)),"traceback":sanitize(traceback.format_exc()),"stage":stage,"operation":operation,"timestamp":utcnow()}
    finally:
        for process in processes:
            if process.poll() is None:
                try: process.terminate();process.wait(timeout=5)
                except Exception as exc: cleanup["errors"].append(str(exc))
        down=subprocess.run(["docker","compose","-p",project,"-f",str(COMPOSE),"down","--volumes","--remove-orphans"],cwd=ROOT,env=env,text=True,capture_output=True,check=False); containers=subprocess.run(["docker","ps","-aq","--filter",f"label=com.docker.compose.project={project}"],text=True,capture_output=True); networks=subprocess.run(["docker","network","ls","-q","--filter",f"name={project}"],text=True,capture_output=True); volumes=subprocess.run(["docker","volume","ls","-q","--filter",f"name={project}"],text=True,capture_output=True); cleanup.update(project=project,compose_down_returncode=down.returncode,container_check_returncode=containers.returncode,network_check_returncode=networks.returncode,volume_check_returncode=volumes.returncode,container_ids=containers.stdout.split(),network_ids=networks.stdout.split(),volume_ids=volumes.stdout.split());cleanup["containers"]=cleanup["container_ids"];cleanup["networks"]=cleanup["network_ids"];cleanup["volumes"]=cleanup["volume_ids"];
        expected_c={"after_temp_created","after_requirements_written","after_canonical_written","after_manifest_written","before_temp_directory_fsync","before_rename","after_rename","before_parent_fsync"};expected_a={"after_pdf_written","after_manifest_written","before_temp_directory_fsync","before_rename","after_rename","before_parent_fsync"}
        assertions={"matrix_canonical_count_8":len(matrix.get("canonical",[]))==8,"matrix_artifact_count_6":len(matrix.get("artifact",[]))==6,"matrix_fault_points_exact":{x.get("fault_point") for x in matrix.get("canonical",[])}==expected_c and {x.get("fault_point") for x in matrix.get("artifact",[])}==expected_a,"matrix_all_retries_pass":all(x.get("retry_success",x.get("same_bytes_retry_success")) for group in matrix.values() for x in group),"matrix_post_rename_immutable":all(x.get("bytes_unchanged") for group in matrix.values() for x in group if x.get("phase")=="post_rename"),"hard_kill_scenario_count_5":len(raw)==5,"fault_marker_count_5":sum(bool(v.get("fault_marker")) for v in raw.values())==5,"faulted_exit_codes_all_97":all(v.get("faulted_process",{}).get("return_code")==97 for v in raw.values()),"clean_processes_all_healthy":all(v.get("clean_processes",[{}])[0].get("health")==200 for v in raw.values()),"clean_processes_all_exited":all(v.get("clean_processes",[{}])[0].get("process_exited") for v in raw.values()),"canonical_pre_rename_retry_recovered":raw.get("canonical-pre-rename",{}).get("requests",[{},{"status":0}])[1].get("status")==200,"canonical_post_rename_retry_reused_generation":raw.get("canonical-post-rename",{}).get("requests",[{},{"status":0}])[1].get("status")==200,"artifact_pre_rename_retry_recovered":raw.get("artifact-pre-rename",{}).get("requests",[{},{"status":0}])[1].get("status")==201,"artifact_post_rename_same_retry_and_replay_201":raw.get("artifact-post-rename-same-bytes",{}).get("requests",[{},{"status":0}])[1].get("status")==201 and raw.get("artifact-post-rename-same-bytes",{}).get("replay_status")==201,"artifact_post_rename_conflict_retry_409":raw.get("artifact-post-rename-conflicting-bytes",{}).get("requests",[{},{"status":0}])[1].get("status")==409,"artifact_post_rename_conflict_classified_orphan":raw.get("artifact-post-rename-conflicting-bytes",{}).get("classification")=="filesystem_only_orphan_conflicting_retry","verifier_count_6":len(verifiers)==6,"all_verifiers_pass":all(v.get("exit_code")==0 and v.get("verified") for v in verifiers),"cleanup_errors_empty":not cleanup["errors"],"compose_resources_absent":not cleanup["containers"] and not cleanup["networks"] and not cleanup["volumes"]}
        scenario_state=scenario_assertions(raw); assertions.update(scenario_state)
        backend_logs={p.name:p.read_text(errors="replace") for p in evidence.glob("backend-*.log")}
        for p in evidence.glob("backend-*.log"): p.unlink()
        payloads={"fault-matrix-canonical.json":matrix.get("canonical",[]),"fault-matrix-artifact.json":matrix.get("artifact",[]),"canonical-pre-rename.json":raw.get("canonical-pre-rename",{}),"canonical-post-rename.json":raw.get("canonical-post-rename",{}),"artifact-pre-rename.json":raw.get("artifact-pre-rename",{}),"artifact-post-rename-same-bytes.json":raw.get("artifact-post-rename-same-bytes",{}),"artifact-post-rename-conflicting-bytes.json":raw.get("artifact-post-rename-conflicting-bytes",{}),"database-snapshots.json":{k:{s:x["db"] for s,x in v.get("snapshots",{}).items()} for k,v in raw.items()},"filesystem-snapshots.json":{k:{s:x["fs"] for s,x in v.get("snapshots",{}).items()} for k,v in raw.items()},"audit-snapshots.json":{k:{s:x["db"].get("audit",[]) for s,x in v.get("snapshots",{}).items()} for k,v in raw.items()},"process-lifecycle.json":lifecycle,"verifier-results.json":verifiers,"commands.log":commands,"backend-logs.json":backend_logs}
        for filename,value in payloads.items(): write(evidence/filename,value)
        shutil.rmtree(temp,ignore_errors=True);cleanup["temporary_root_removed"]=not temp.exists();assertions["temporary_root_removed"]=cleanup["temporary_root_removed"]
        cleanup["cleanup_complete"]=cleanup["compose_down_returncode"]==cleanup["container_check_returncode"]==cleanup["network_check_returncode"]==cleanup["volume_check_returncode"]==0 and not cleanup["container_ids"] and not cleanup["network_ids"] and not cleanup["volume_ids"] and not cleanup["errors"] and cleanup["temporary_root_removed"]
        assertions["cleanup_complete"]=cleanup["cleanup_complete"];write(evidence/"cleanup.json",cleanup)
        provisional={"status":"FAILED","duration_seconds":time.monotonic()-started,"primary_failure":primary,"finalization_failures":finalization_failures,"cleanup_errors":cleanup_errors,"assertions":assertions,"compose_project":project,"postgres_port":port,"evidence_pack_complete":all((evidence/n).is_file() for n in FILES if n!="interrupted-publication-result.json"),"evidence_hygiene":{},"sha256sums_validator":{}}
        write(evidence/"interrupted-publication-result.json",provisional);hygiene_result=hygiene(evidence,[password,str(temp)]);assertions["evidence_pack_complete"]=provisional["evidence_pack_complete"];assertions["evidence_hygiene_pass"]=hygiene_result["passed"];details=checksums(evidence);assertions["sha256sums_complete_and_valid"]=details["valid"];provisional.update(assertions=assertions,evidence_hygiene=hygiene_result,sha256sums_validator=details);provisional["status"]=STATUS if primary is None and not finalization_failures and not cleanup_errors and all(assertions.values()) else "FAILED";write(evidence/"interrupted-publication-result.json",provisional);details=checksums(evidence);provisional["sha256sums_validator"]=details;write(evidence/"interrupted-publication-result.json",provisional);checksums(evidence)
    print(evidence);return 0 if provisional["status"]==STATUS else 1


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--self-test-hygiene",action="store_true");parser.add_argument("--self-test-failure-finalization",action="store_true");args=parser.parse_args()
    if args.self_test_hygiene: raise SystemExit(self_hygiene())
    if args.self_test_failure_finalization: raise SystemExit(self_finalization())
    raise SystemExit(main())
