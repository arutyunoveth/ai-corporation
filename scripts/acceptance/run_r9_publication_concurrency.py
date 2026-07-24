"""Disposable three-process HTTP evidence for R9.4 publication races."""
from __future__ import annotations
import argparse, hashlib, json, os, re, secrets, shutil, socket, subprocess, sys, tempfile, threading, time, traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[2]; COMPOSE=ROOT/"tests/integration/compose.r8-postgres.yml"; sys.path.insert(0,str(ROOT/"scripts"/"acceptance"))
from r8_acceptance.runtime import http  # noqa: E402
STATUS="R9_4_FINAL_PDF_PUBLICATION_CONCURRENCY_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL"
FILES=("publication-concurrency-result.json","scenario-identical.json","scenario-conflicting.json","publication-attempts.json","renderer-barriers.json","application-lifecycle.json","database-snapshots.json","audit-snapshots.json","filesystem-snapshots.json","verifier-results.json","artifact-bindings.json","postgres-identity.json","commands.log","backend-a.log","backend-a2.log","backend-b.log","cleanup.json")

def now(): return datetime.now(UTC).isoformat()
def free():
    with socket.socket() as s: s.bind(("127.0.0.1",0)); return s.getsockname()[1]
def sanitize(value:Any)->Any:
    if isinstance(value,dict): return {str(k):sanitize(v) for k,v in value.items()}
    if isinstance(value,list): return [sanitize(v) for v in value]
    if not isinstance(value,str): return value
    value=re.sub(r"postgres(?:ql)?(?:\+\w+)?://[^\s\"']+","<postgres-url>",value)
    value=re.sub(r"(?i)(password|authorization|cookie|token)\s*[=:]\s*[^\s,;\"']+",r"\1=<redacted>",value)
    value=re.sub(r"/Users/[^\s\"']+/(?:output/)?r9-concurrency-[^\s\"']+","<temporary-root>",value)
    return value
def write(p:Path,v:Any): p.write_text(json.dumps(sanitize(v),default=str,sort_keys=True,indent=2)+"\n")
def sha(b:bytes): return hashlib.sha256(b).hexdigest()
def hygiene_ok(path:Path)->bool:
    blob="\n".join(p.read_text(errors="replace") for p in path.iterdir() if p.is_file() and p.name!="SHA256SUMS")
    return not any(re.search(pattern,blob,re.I) for pattern in (r"postgres(?:ql)?(?:\+\w+)?://",r"password\s*[=:]\s*(?!<redacted>)",r"authorization\s*[=:]\s*(?!<redacted>)",r"cookie\s*[=:]\s*(?!<redacted>)",r"token\s*[=:]\s*(?!<redacted>)",r"/Users/.+/r9-concurrency-"))
def checksum_details(evidence:Path)->dict[str,Any]:
    expected=set(FILES); present={p.name for p in evidence.iterdir() if p.is_file() and p.name!="SHA256SUMS"}; missing=sorted(expected-present); unexpected=sorted(present-expected)
    lines=[]
    if not missing and not unexpected:
        lines=[f"{sha((evidence/name).read_bytes())}  {name}" for name in sorted(expected)]
        (evidence/"SHA256SUMS").write_text("\n".join(lines)+"\n")
    parsed=[]
    if (evidence/"SHA256SUMS").exists():
        parsed=[line.split("  ",1) for line in (evidence/"SHA256SUMS").read_text().splitlines() if "  " in line]
    names=[item[1] for item in parsed]; mismatches=[name for digest,name in parsed if not (evidence/name).is_file() or sha((evidence/name).read_bytes())!=digest]
    return {"valid":not missing and not unexpected and len(parsed)==len(expected) and len(names)==len(set(names)) and set(names)==expected and not mismatches and "SHA256SUMS" not in names,"entry_count":len(parsed),"expected_file_count":len(expected),"duplicate_files":sorted({n for n in names if names.count(n)>1}),"missing_files":missing,"unexpected_files":unexpected,"hash_mismatches":mismatches,"self_included":"SHA256SUMS" in names}
def run(cmd,env,log):
    r=subprocess.run(cmd,cwd=ROOT,env=env,text=True,capture_output=True,check=False,timeout=90); log.append({"command":cmd,"returncode":r.returncode,"stdout":r.stdout[-2000:],"stderr":r.stderr[-2000:]});
    if r.returncode: raise RuntimeError(f"command failed: {cmd}")
def health(port,proc,lifecycle):
    for _ in range(100):
        if proc.poll() is not None: raise RuntimeError(f"{lifecycle['label']} exited early {proc.returncode}")
        try:
            status,_,_=http("GET",f"http://127.0.0.1:{port}/health",username="",password="")
            if status==200: lifecycle.update(health_status=200,healthy_at=now()); return
        except Exception: pass
        time.sleep(.1)
    raise RuntimeError("health timeout")
def snapshot(env,state,data):
    code='''import json,os,hashlib
from pathlib import Path
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotRunResult,PilotAuditEvent,ProcurementCase
from src.tender_research.models import TenderAnalysisRun
s=json.loads(os.environ["R9_STATE"]); root=Path(os.environ["AI_CORP_ARVECTUM_DATA_DIR"])
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as x:
 a=x.scalar(select(PilotArtifact).where(PilotArtifact.run_id==s["run_id"])); r=x.scalar(select(PilotRunResult).where(PilotRunResult.run_id==s["run_id"])); run=x.get(TenderAnalysisRun,s["run_id"]); c=x.get(ProcurementCase,s["case_id"]); aud=x.scalars(select(PilotAuditEvent).where(PilotAuditEvent.run_id==s["run_id"]).order_by(PilotAuditEvent.created_at,PilotAuditEvent.id)).all()
 def row(o): return {k:str(getattr(o,k,None)) if k.endswith("_at") else getattr(o,k,None) for k in o.__table__.columns.keys()} if o else None
 out={"artifact":row(a),"run_result":row(r),"run":row(run),"case":row(c),"audit":[row(i) for i in aud],"counts":{"artifact":1 if a else 0,"run_result":1 if r else 0,"audit_exported":sum(i.event_type=="artifact_exported" for i in aud)}}
 artifacts=Path(a.pdf_relative_path.split("/artifacts/",1)[0]+"/artifacts") if a else None
 out["filesystem"]={"artifacts_root":str(artifacts) if artifacts else None,"generation_directories":[],"partial_or_temp":[]}
 if a:
  d=root/a.pdf_relative_path; m=root/a.manifest_relative_path; ar=root/artifacts; files=[]
  for p in sorted(d.parent.iterdir()): files.append({"name":p.name,"relative_path":str(p.relative_to(root)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"byte_size":p.stat().st_size,"mtime_ns":p.stat().st_mtime_ns,"mode":oct(p.stat().st_mode & 0o777)})
  out["filesystem"].update({"generation":d.parent.name,"generation_directories":sorted(p.name for p in ar.iterdir() if p.is_dir()),"entries":[p["name"] for p in files],"files":files,"pdf_sha256":hashlib.sha256(d.read_bytes()).hexdigest(),"manifest_sha256":hashlib.sha256(m.read_bytes()).hexdigest(),"pdf_mtime_ns":d.stat().st_mtime_ns,"manifest_mtime_ns":m.stat().st_mtime_ns,"manifest":json.loads(m.read_text()),"partial_or_temp":sorted(str(p.relative_to(root)) for p in ar.rglob("*") if p.name.endswith((".tmp",".partial")))})
 print(json.dumps(out,default=str))'''
    e=env.copy();e["R9_STATE"]=json.dumps(state); r=subprocess.run([sys.executable,"-c",code],cwd=ROOT,env=e,text=True,capture_output=True,check=False,timeout=30)
    if r.returncode: raise RuntimeError(r.stderr)
    return json.loads(r.stdout)
def verifier(env,state,stage):
    code='''import json,os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotRunResult,ProcurementCase
from src.modules.customer_pilot.binding_verifier import verify_run_snapshot_binding
from src.modules.customer_pilot.artifacts import verified_pilot_artifact
from src.tender_research.models import TenderAnalysisRun
s=json.loads(os.environ["R9_STATE"])
with Session(create_engine(os.environ["AI_CORP_DATABASE_URL"])) as x:
 run=x.get(TenderAnalysisRun,s["run_id"]); case=x.get(ProcurementCase,s["case_id"]); binding=x.query(PilotRunResult).filter_by(run_id=s["run_id"]).one(); artifact=x.query(PilotArtifact).filter_by(run_id=s["run_id"]).one()
 verify_run_snapshot_binding(run=run,case=case,binding=binding); verified_pilot_artifact(run,case,binding,artifact)
 print(json.dumps({"canonical":True,"artifact":True,"expected_pdf_sha256":artifact.pdf_sha256,"actual_pdf_sha256":artifact.pdf_sha256}))'''
    local=env.copy(); local["R9_STATE"]=json.dumps(state); result=subprocess.run([sys.executable,"-c",code],cwd=ROOT,env=local,text=True,capture_output=True,check=False,timeout=30)
    data={"scenario":state["scenario"],"stage":stage,"exit_code":result.returncode,"canonical":False,"artifact":False,"sanitized_stdout":sanitize(result.stdout[-2000:]),"sanitized_stderr":sanitize(result.stderr[-2000:])}
    if result.returncode==0:
        try: data.update(json.loads(result.stdout))
        except json.JSONDecodeError: data["parse_error"]=True
    return data
def bootstrap(path:Path):
    path.write_text('''import os,json,time,hashlib,sys
from pathlib import Path
sys.path.insert(0,os.environ["R9_REPOSITORY_ROOT"])
label=os.environ["R9_LABEL"]; payload=bytes.fromhex(os.environ["R9_PAYLOAD"]); root=Path(os.environ["R9_BARRIER_ROOT"])
from src.modules.tender_operator_agent_demo import report_export_service
print(json.dumps({"event":"bootstrap_started","process_label":label,"pid":os.getpid()}),flush=True)
def render(canonical,title,output):
 control=json.loads((root/"scenario.json").read_text()); scenario=control["name"]; expected=set(control["labels"])
 if label not in expected: raise RuntimeError("unexpected renderer label")
 d=root/scenario; d.mkdir(parents=True,exist_ok=True); marker=d/(label+".json"); tmp=d/(label+".tmp"); tmp.write_text(json.dumps({"scenario":scenario,"process_label":label,"pid":os.getpid(),"candidate_sha256":hashlib.sha256(payload).hexdigest(),"candidate_byte_size":len(payload),"entered_at":time.time(),"entered_monotonic":time.monotonic()})); os.replace(tmp,marker); print(json.dumps({"event":"renderer_entered","scenario":scenario,"process_label":label}),flush=True)
 deadline=time.monotonic()+15
 while {p.stem for p in d.glob("*.json") if p.stem in expected} != expected:
  if time.monotonic()>deadline: raise RuntimeError("renderer barrier timeout")
  time.sleep(.01)
 item=json.loads(marker.read_text()); item["released_at"]=time.time(); marker.write_text(json.dumps(item)); output.write_bytes(payload); (d/(label+".complete")).write_text(json.dumps({"process_label":label,"completed_at":time.time()})); print(json.dumps({"event":"renderer_released","scenario":scenario,"process_label":label}),flush=True)
report_export_service._build_pdf_from_canonical=render
print(json.dumps({"event":"renderer_patched","process_label":label}),flush=True)
from src.main import app
print(json.dumps({"event":"app_imported","process_label":label}),flush=True)
import uvicorn
print(json.dumps({"event":"uvicorn_started","process_label":label}),flush=True)
try: uvicorn.run(app,host="127.0.0.1",port=int(os.environ["R9_PORT"]))
finally: print(json.dumps({"event":"shutdown","process_label":label}),flush=True)''')
def main():
 evidence=ROOT/"output"/f"r9-publication-concurrency-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"; evidence.mkdir(parents=True); started=time.monotonic(); stage="initialize"; operation="create disposable environment"; temp=Path(tempfile.mkdtemp(prefix="r9-concurrency-",dir=ROOT/"output")); data=temp/"data"; data.mkdir(); barrier=temp/"barrier"; barrier.mkdir(); commands=[]; lifecycle={}; attempts=[]; raw={"identical":{},"conflicting":{}}; primary=None; finalization_failures=[]; cleanup_errors=[]; procs={}; cleanup={"errors":[]}; password="r9-"+secrets.token_urlsafe(16); pg=free(); project="r9conc"+secrets.token_hex(4); env=os.environ.copy(); env.update(R8_POSTGRES_PASSWORD=password,R8_POSTGRES_PORT=str(pg),AI_CORP_DATABASE_URL=f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{pg}/r8_acceptance",AI_CORP_ARVECTUM_DATA_DIR=str(data),AI_CORP_PILOT_AUTH_ENABLED="false",AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED="false")
 A=b"%PDF-1.4\\nR9-RUNTIME-PAYLOAD-A\\n%%EOF\\n"; B=b"%PDF-1.4\\nR9-RUNTIME-PAYLOAD-B\\n%%EOF\\n"; assert len(A)==len(B) and sha(A)!=sha(B)
 try:
  stage="bootstrap_write"; operation="write renderer-first bootstrap"; boot=temp/"bootstrap.py"; bootstrap(boot); compose=["docker","compose","-p",project,"-f",str(COMPOSE)]; stage="compose_up"; operation="start disposable PostgreSQL"; run(compose+["up","-d","--wait"],env,commands); stage="alembic_upgrade"; operation="apply migrations"; run([sys.executable,"-m","alembic","upgrade","head"],env,commands)
  stage="seed_identical"; operation="seed canonical fixture and customer"
  seed='import os,sys;sys.path.insert(0,"scripts/acceptance");from run_r8_acceptance import _seed;_seed(os.environ);from sqlalchemy import create_engine;from sqlalchemy.orm import Session;from src.modules.customer_registry.models import CustomerProfile;s=Session(create_engine(os.environ["AI_CORP_DATABASE_URL"]));s.add(CustomerProfile(customer_id="R9-RUNTIME",legal_name="R9",customer_status="prospect"));s.commit()'; run([sys.executable,"-c",seed],env,commands)
  for label,payload in (("A",A),("A2",A),("B",B)):
   stage=f"process_start_{label.lower()}"; operation=f"start backend {label}"
   port=free(); log=evidence/f"backend-{label.lower()}.log"; e=env.copy(); e.update(R9_LABEL=label,R9_PAYLOAD=payload.hex(),R9_BARRIER_ROOT=str(barrier),R9_PORT=str(port),R9_REPOSITORY_ROOT=str(ROOT)); p=subprocess.Popen([sys.executable,str(boot)],cwd=ROOT,env=e,stdout=log.open("w"),stderr=subprocess.STDOUT); procs[label]=p; lifecycle[label]={"label":label,"pid":p.pid,"port":port,"start_requested_at":now()}; stage=f"health_{label.lower()}"; operation=f"wait for backend {label}"; health(port,p,lifecycle[label]);
   with log.open("a") as handle: handle.write(json.dumps({"event":"health_reached","process_label":label})+"\n")
  base=lambda label:f"http://127.0.0.1:{lifecycle[label]['port']}/api/operator/pilot/customers/R9-RUNTIME"
  def setup(name,n):
   nonlocal stage,operation
   stage=f"seed_{name}"; operation=f"create completed {name} run"
   st,body,_=http("POST",base("A")+"/projects",username="",password="",body={"name":name}); proj=json.loads(body); st,body,_=http("POST",base("A")+f"/projects/{proj['id']}/cases",username="",password="",body={"procurement_number":n}); case=json.loads(body); st,body,_=http("POST",base("A")+f"/cases/{case['id']}/runs",username="",password="",body={},headers={"Idempotency-Key":name}); r=json.loads(body); http("POST",base("A")+f"/cases/{case['id']}/runs/{r['id']}/complete",username="",password="",body={}); return {"scenario":name,"project_id":proj["id"],"case_id":case["id"],"run_id":r["id"]}
  def race(name,labels,state):
   nonlocal stage,operation
   shutil.rmtree(barrier/name,ignore_errors=True); stage=f"snapshot_pre_{name}"; operation="capture state before race"; pre=snapshot(env,state,data); gate=threading.Barrier(2)
   def one(label):
    gate.wait(); start=time.monotonic(); st,body,_=http("POST",base(label)+f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf",username="",password=""); end=time.monotonic(); item={"scenario":name,"target_process":label,"started_monotonic":start,"completed_monotonic":end,"started_at":now(),"completed_at":now(),"duration":end-start,"status":st,"response":json.loads(body)};attempts.append(item);return item
   for label in labels: procs[label].send_signal(0)
   (barrier/"scenario.json").write_text(json.dumps({"name":name,"labels":labels})); stage=f"race_{name}"; operation="send concurrent HTTP publication requests"
   with ThreadPoolExecutor(max_workers=2) as x: result=list(x.map(one,labels))
   markers=[json.loads(p.read_text()) for p in sorted((barrier/name).glob("*.json"))]; stage=f"snapshot_post_{name}"; operation="capture state after race"; post=snapshot(env,state,data); stage="verifiers"; operation=f"fresh verifier after {name} race"; post_verifier=verifier(env,state,"post_race"); marker_count=len(markers); stage=f"replay_{name}"; operation="send sequential replay"; replay=http("POST",base("A")+f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf",username="",password=""); attempts.append({"scenario":name,"kind":"replay","target_process":"A","port":lifecycle["A"]["port"],"status":replay[0],"response":json.loads(replay[1])}); stage=f"snapshot_replay_{name}"; operation="capture state after replay"; after=snapshot(env,state,data); stage="verifiers"; operation=f"fresh verifier after {name} replay"; replay_verifier=verifier(env,state,"post_replay"); raw[name]={"state":state,"pre_snapshot":pre,"attempts":result,"markers":markers,"completions":[p.name for p in (barrier/name).glob("*.complete")],"post_snapshot":post,"replay_status":replay[0],"after_replay_snapshot":after,"replay_marker_count_unchanged":marker_count==len(list((barrier/name).glob("*.json"))),"verifier_results":[post_verifier,replay_verifier]}
  identical=setup("identical","0379100000726000101"); race("identical",("A","A2"),identical)
  conflicting=setup("conflicting","0379100000726000101"); race("conflicting",("A","B"),conflicting)
 except Exception as exc: primary={"type":type(exc).__name__,"message":str(exc),"traceback":traceback.format_exc(),"stage":stage,"operation":operation,"timestamp":now()}
 finally:
  stage="process_cleanup"; operation="stop backend processes"
  for label,p in procs.items():
   try:p.terminate();p.wait(timeout=5);lifecycle[label].update(return_code=p.returncode,process_exited=True,exited_at=now());
   except Exception as exc:lifecycle[label]["stop_error"]=str(exc);cleanup["errors"].append({"operation":f"stop {label}","type":type(exc).__name__,"message":str(exc)})
   finally:
    with (evidence/f"backend-{label.lower()}.log").open("a") as handle: handle.write(json.dumps({"event":"shutdown","process_label":label})+"\n")
  try:
   stage="compose_cleanup"; operation="remove compose resources"; down=subprocess.run(["docker","compose","-p",project,"-f",str(COMPOSE),"down","--volumes","--remove-orphans"],cwd=ROOT,env=env,text=True,capture_output=True,check=False,timeout=90); cleanup.update({"temporary_root":str(temp),"compose_project":project,"down_returncode":down.returncode});
   for key,cmd in {"container_ids":["docker","compose","-p",project,"-f",str(COMPOSE),"ps","-aq"],"network_ids":["docker","network","ls","--filter",f"name={project}","-q"],"volume_ids":["docker","volume","ls","--filter",f"name={project}","-q"]}.items():
    check=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,check=False,timeout=30); cleanup[key]=check.stdout.split(); cleanup["errors"] += [] if check.returncode==0 else [{"operation":key,"type":"CleanupCheckError","message":check.stderr[-500:]}]
  finally: pass
  def contract(name,labels,statuses):
   value=raw[name]; post=value.get("post_snapshot",{}); after=value.get("after_replay_snapshot",{}); fs=post.get("filesystem",{}); observed=[item.get("status") for item in value.get("attempts",[])]; marker_labels={item.get("process_label") for item in value.get("markers",[])}; marker_hashes={item.get("candidate_sha256") for item in value.get("markers",[])}; responses=[item.get("response",{}) for item in value.get("attempts",[])]; overlapping=max(item.get("started_monotonic",0) for item in value.get("attempts",[])) < min(item.get("completed_monotonic",0) for item in value.get("attempts",[])) if len(value.get("attempts",[]))==2 else False
   same_snapshot=post==after
   identical_response=len({tuple(sorted((key,str(response.get(key))) for key in ("id","artifact_key","pdf_sha256","byte_size"))) for response in responses})==1
   winner=post.get("artifact",{}).get("pdf_sha256"); loser=next(iter(marker_hashes-{winner}),None)
   conflict_safe=all("id" not in response for item,response in zip(value.get("attempts",[]),responses) if item.get("status")==409)
   ok=sorted(observed)==sorted(statuses) and marker_labels==set(labels) and {p.removesuffix(".complete") for p in value.get("completions",[])}==set(labels) and overlapping and post.get("counts")=={"artifact":1,"run_result":1,"audit_exported":1} and fs.get("entries")==["artifact.manifest.json","final.pdf"] and value.get("replay_status")==201 and value.get("replay_marker_count_unchanged") and same_snapshot
   ok=ok and (identical_response if name=="identical" else len(marker_hashes)==2 and all(item.get("candidate_byte_size")==39 for item in value.get("markers",[])) and winner in marker_hashes and loser and loser not in json.dumps(post) and conflict_safe)
   return {"name":name,"ok":ok,"observed_statuses":observed,"marker_labels":sorted(marker_labels),"marker_hashes":sorted(marker_hashes),"overlapping_intervals":overlapping,"replay_unchanged":same_snapshot,"replay_marker_count_unchanged":value.get("replay_marker_count_unchanged")}
  criteria=[contract("identical",("A","A2"),(201,201)),contract("conflicting",("A","B"),(201,409))]
  stage="verifiers"; operation="evaluate raw runtime contract"; cleanup_complete=not cleanup["errors"] and not cleanup.get("container_ids") and not cleanup.get("network_ids") and not cleanup.get("volume_ids") and cleanup.get("down_returncode")==0
  verifier_results=[item for value in raw.values() for item in value.get("verifier_results",[])]
  completeness={"application_processes":len(lifecycle)==3,"scenarios":len(raw)==2,"concurrent_attempts":len([x for x in attempts if x.get("kind")!="replay"])==4,"replay_attempts":len([x for x in attempts if x.get("kind")=="replay"])==2,"identical_entry_markers":len(raw["identical"].get("markers",[]))==2,"identical_completion_markers":len(raw["identical"].get("completions",[]))==2,"conflicting_entry_markers":len(raw["conflicting"].get("markers",[]))==2,"conflicting_completion_markers":len(raw["conflicting"].get("completions",[]))==2,"database_snapshots":all(all(v.get(k) is not None for k in ("pre_snapshot","post_snapshot","after_replay_snapshot")) for v in raw.values()),"audit_snapshots":all(all(v.get(k) is not None for k in ("pre_snapshot","post_snapshot","after_replay_snapshot")) for v in raw.values()),"filesystem_snapshots":all(all(v.get(k) is not None for k in ("pre_snapshot","post_snapshot","after_replay_snapshot")) for v in raw.values()),"verifier_results":len(verifier_results)==4}
  verifier_ok=all(v.get("exit_code")==0 and v.get("canonical") is True and v.get("artifact") is True and v.get("expected_pdf_sha256")==v.get("actual_pdf_sha256") for v in verifier_results)
  assertions={"runtime_contract":all(item["ok"] for item in criteria),"completeness":all(completeness.values()),"fresh_verifiers":verifier_ok,"cleanup_complete":cleanup_complete,"processes_exited":all(v.get("process_exited") for v in lifecycle.values())}
  if not primary and not all(assertions.values()): primary={"type":"RuntimeContractError","message":"raw concurrency criteria, completeness, verifier, or cleanup not satisfied","criteria":criteria,"assertions":assertions,"stage":stage,"operation":operation,"timestamp":now()}
  stage="evidence_write"; operation="write final evidence files"
  cleanup_errors.extend(cleanup["errors"])
  try: shutil.rmtree(temp); cleanup["temporary_root_removed"]=not temp.exists()
  except Exception as exc: cleanup_errors.append({"type":type(exc).__name__,"message":str(exc),"operation":"remove temporary root"}); cleanup["temporary_root_removed"]=False
  databases={k:{"pre_race":v.get("pre_snapshot"),"post_race":v.get("post_snapshot"),"post_replay":v.get("after_replay_snapshot")} for k,v in raw.items()}
  bindings={k:{"response":[a["response"] for a in v.get("attempts",[])],"artifact":v.get("post_snapshot",{}).get("artifact"),"manifest":v.get("post_snapshot",{}).get("filesystem",{}).get("manifest")} for k,v in raw.items()}
  payloads={"scenario-identical.json":raw["identical"],"scenario-conflicting.json":raw["conflicting"],"publication-attempts.json":attempts,"renderer-barriers.json":raw,"application-lifecycle.json":lifecycle,"database-snapshots.json":databases,"audit-snapshots.json":databases,"filesystem-snapshots.json":databases,"verifier-results.json":verifier_results,"artifact-bindings.json":bindings,"postgres-identity.json":{"compose_project":project,"postgres_port":pg,"database":"r8_acceptance"},"commands.log":commands,"cleanup.json":cleanup}
  for name,value in payloads.items():
   try: write(evidence/name,value)
   except Exception as exc: finalization_failures.append({"type":type(exc).__name__,"message":sanitize(str(exc)),"operation":f"write {name}"})
  preliminary={"duration_seconds":time.monotonic()-started,"compose_project":project,"postgres_port":pg,"criteria":criteria,"completeness":completeness,"assertions":assertions,"primary_failure":primary,"finalization_failures":finalization_failures,"cleanup_errors":cleanup_errors,"evidence_hygiene_pass":False,"sha256sums_validator":{},"evidence_pack_complete":False,"status":"FAILED"}
  try: write(evidence/"publication-concurrency-result.json",preliminary)
  except Exception as exc: finalization_failures.append({"type":type(exc).__name__,"message":sanitize(str(exc)),"operation":"write result"})
  hygiene=hygiene_ok(evidence); complete=all((evidence/name).is_file() for name in FILES); details=checksum_details(evidence)
  result={**preliminary,"finalization_failures":finalization_failures,"evidence_hygiene_pass":hygiene,"evidence_pack_complete":complete,"sha256sums_validator":details}
  result["status"]=STATUS if primary is None and not finalization_failures and not cleanup_errors and all(assertions.values()) and complete and hygiene and details["valid"] and cleanup.get("temporary_root_removed") else "FAILED"
  write(evidence/"publication-concurrency-result.json",result); details=checksum_details(evidence); result["sha256sums_validator"]=details; write(evidence/"publication-concurrency-result.json",result); details=checksum_details(evidence); result["sha256sums_validator"]=details; write(evidence/"publication-concurrency-result.json",result); checksum_details(evidence)
 print(evidence); return 0 if result["status"]==STATUS else 1
def self_test_hygiene()->int:
 root=Path(tempfile.mkdtemp(prefix="r9-hygiene-"));
 try:
  sample={"safe":{"status":201,"hash":"a"*64,"count":1},"secret":"postgresql://user:pass@host/db password=SYNTHETIC Authorization: Bearer synthetic Cookie=abc token=xyz /Users/test/output/r9-concurrency-secret"}; write(root/"sample.json",sample); text=(root/"sample.json").read_text(); return 0 if hygiene_ok(root) and "SYNTHETIC" not in text and '"status": 201' in text else 1
 finally: shutil.rmtree(root,ignore_errors=True)
def self_test_failure_finalization()->int:
 root=Path(tempfile.mkdtemp(prefix="r9-finalization-"));
 try:
  primary={"type":"InjectedWorkflowError","stage":"initialize"}; write(root/"before-start.json",{"primary_failure":primary,"compose":"not_started","processes":"not_started","status":"FAILED"}); first=(root/"before-start.json").is_file()
  failures=[{"type":"OSError","operation":"write optional evidence"}]; write(root/"partial-result.json",{"primary_failure":primary,"finalization_failures":failures,"cleanup":"continued","evidence_pack_complete":False,"status":"FAILED"}); write(root/"remaining.json",{"partial":True}); entries=sorted(p for p in root.iterdir() if p.is_file()); (root/"SHA256SUMS").write_text("".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in entries)); valid=all(sha((root/name).read_bytes())==digest for digest,name in (line.split("  ",1) for line in (root/"SHA256SUMS").read_text().splitlines())); return 0 if first and failures and valid else 1
 finally: shutil.rmtree(root,ignore_errors=True)
if __name__=="__main__":
 parser=argparse.ArgumentParser(); parser.add_argument("--self-test-hygiene",action="store_true"); parser.add_argument("--self-test-failure-finalization",action="store_true"); args=parser.parse_args()
 raise SystemExit(self_test_hygiene() if args.self_test_hygiene else self_test_failure_finalization() if args.self_test_failure_finalization else main())
