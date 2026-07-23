"""Disposable R9.1 smoke: one published customer result across one app restart."""
from __future__ import annotations

import hashlib, json, os, secrets, shutil, subprocess, sys, tempfile, time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "acceptance"))
from r8_acceptance.runtime import Uvicorn, free_port, http  # noqa: E402
from run_r8_acceptance import _seed, _prepare_customer, _enrich_states, snapshot_business_db, snapshot_audit, snapshot_filesystem  # noqa: E402

COMPOSE = ROOT / "tests/integration/compose.r8-postgres.yml"
CUSTOMER = "R9-RESTART-SYNTHETIC"

def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)+"\n")
def now(): return datetime.now(UTC).isoformat()
def command(args, env, log):
    r=subprocess.run(args,cwd=ROOT,env=env,text=True,capture_output=True); log.append({"command":" ".join(args),"exit_code":r.returncode,"stdout":r.stdout,"stderr":r.stderr})
    if r.returncode: raise RuntimeError(r.stderr or r.stdout)
    return r
def status(url):
    try: return http("GET",url,username="",password="")[0]
    except OSError: return None
def revision(env, log):
    code="from sqlalchemy import create_engine,text;import os;print(create_engine(os.environ['AI_CORP_DATABASE_URL']).connect().execute(text('select version_num from alembic_version')).scalar_one())"
    return command([sys.executable,"-c",code],env,log).stdout.strip()
def verifiers(env, state):
    code = """
import json,os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotReview,PilotRunResult,ProcurementCase
from src.tender_research.models import TenderAnalysisRun
from src.modules.customer_pilot.binding_verifier import verify_run_snapshot_binding
from src.modules.customer_pilot.artifacts import verified_pilot_artifact,verify_review_artifact_binding
s=json.loads(os.environ['R9_STATE']); e=create_engine(os.environ['AI_CORP_DATABASE_URL'])
with Session(e) as x:
 r=x.get(PilotRunResult,s['run_result_id']); a=x.get(PilotArtifact,s['artifact_id']); v=x.get(PilotReview,s['review_id']); c=x.get(ProcurementCase,s['case_id']); run=x.get(TenderAnalysisRun,s['run_id'])
 b=verify_run_snapshot_binding(run=run,case=c,binding=r); aa=verified_pilot_artifact(run, c, r, a); verify_review_artifact_binding(review=v,run=run,case=c,result=r,artifact=a,verified_artifact=aa)
 print(json.dumps({'canonical':'PASS','artifact':'PASS','review':'PASS','canonical_hash':b.canonical_report_file_sha256,'pdf_sha256':aa.pdf_sha256,'review_artifact_id':str(v.artifact_id)}))
"""
    e=env.copy();e["R9_STATE"]=json.dumps(state)
    r=subprocess.run([sys.executable,"-c",code],cwd=ROOT,env=e,text=True,capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr)
    return json.loads(r.stdout)
def pg_identity(project):
    r=subprocess.run(["docker","compose","-p",project,"-f",str(COMPOSE),"ps","-q","postgres"],cwd=ROOT,text=True,capture_output=True)
    cid=r.stdout.strip(); inspect=subprocess.run(["docker","inspect",cid,"--format","{{.Id}} {{.State.StartedAt}} {{.RestartCount}}"],text=True,capture_output=True).stdout.strip().split()
    return {"id":inspect[0],"started_at":inspect[1],"restart_count":inspect[2]}
def sums(evidence):
    (evidence/"SHA256SUMS").write_text("\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(evidence.iterdir()) if p.is_file() and p.name!="SHA256SUMS")+"\n")
def main():
    stamp=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"); evidence=ROOT/"output"/f"r9-application-restart-{stamp}";evidence.mkdir(parents=True)
    temp=Path(tempfile.mkdtemp(prefix="r9-restart-",dir=ROOT/"output"));data=temp/"data";data.mkdir();pg,api=free_port(),free_port();assert pg!=api
    password="r9-"+secrets.token_urlsafe(20);project="r9restart"+secrets.token_hex(5);url=f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{pg}/r8_acceptance"
    env=os.environ.copy();env.update({"R8_POSTGRES_PASSWORD":password,"R8_POSTGRES_PORT":str(pg),"AI_CORP_DATABASE_URL":url,"AI_CORP_ARVECTUM_DATA_DIR":str(data),"AI_CORP_PILOT_AUTH_ENABLED":"false","AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED":"false"})
    commands=[]; first=second=None; cleanup={}; result={"status":"FAILED","assertions":{}}; state={}
    try:
        compose=["docker","compose","-p",project,"-f",str(COMPOSE)]; command(compose+["up","-d","--wait"],env,commands); command([sys.executable,"-m","alembic","upgrade","head"],env,commands); assert revision(env,commands)=="096_add_r8_canonical_snapshot_binding"
        _seed(env)
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from src.modules.customer_registry.models import CustomerProfile
        with Session(create_engine(env["AI_CORP_DATABASE_URL"])) as session:
            session.add(CustomerProfile(customer_id=CUSTOMER, legal_name="R9 synthetic customer", customer_status="prospect")); session.commit()
        first=Uvicorn(root=ROOT,env=env,port=api,log=evidence/"backend-first.log");first.start("first");first.wait_ready("","")
        base=f"http://127.0.0.1:{api}/api/operator/pilot/customers/{{customer}}";state=_prepare_customer(base,"","",CUSTOMER);_enrich_states(env,[state])
        case_status,case_body,_=http("GET",base.format(customer=CUSTOMER)+f"/cases/{state['case_id']}",username="",password=""); assert case_status==200 and json.loads(case_body)["status"]=="delivered"
        pdf_url=base.format(customer=CUSTOMER)+f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf";s,pdf,_=http("GET",pdf_url,username="",password="");assert s==200
        pre_db={"business":snapshot_business_db(env),"audit":snapshot_audit(env)};pre_fs=snapshot_filesystem(data);pre_v=verifiers(env,state);pg_pre=pg_identity(project)
        first_pid=first.process.pid;first_process=first.process;first.stop("first"); first_return=first_process.returncode; assert status(f"http://127.0.0.1:{api}/health") is None
        second=Uvicorn(root=ROOT,env=env,port=api,log=evidence/"backend-second.log");second.start("second");second.wait_ready("","");assert second.process.pid!=first_pid
        s,pdf_after,_=http("GET",pdf_url,username="",password="");assert s==200
        post_db={"business":snapshot_business_db(env),"audit":snapshot_audit(env)};post_fs=snapshot_filesystem(data);post_v=verifiers(env,state);pg_post=pg_identity(project)
        second_pid=second.process.pid; assertions={"different_pids":second_pid!=first_pid,"health_both":True,"postgres_unchanged":pg_pre==pg_post,"alembic_096":revision(env,commands)=="096_add_r8_canonical_snapshot_binding","db_equal":pre_db==post_db,"filesystem_equal":pre_fs==post_fs,"verifiers_pass":pre_v==post_v,"pdf_equal":pdf==pdf_after,"pdf_hash_matches":hashlib.sha256(pdf).hexdigest()==state["pdf_sha256"],"no_partials":not any(".partial." in p for p in pre_fs),"one_result_artifact_review":all(v["count"]==1 for k,v in pre_db["business"].items() if k in {"PilotRunResult","PilotArtifact","PilotReview"})}
        assert all(assertions.values()),assertions;result={"status":"R9_1_APPLICATION_RESTART_SMOKE_PASS_LOCAL_EVIDENCE","assertions":assertions,"ids":state,"http":{"first_health":200,"second_health":200,"pdf_pre":200,"pdf_post":200},"pids":{"first":first_pid,"second":second_pid},"return_codes":{"first":first_return},"pdf_sha256":hashlib.sha256(pdf).hexdigest()}
        write(evidence/"database-snapshots.json",{"pre":pre_db,"post":post_db});write(evidence/"filesystem-snapshots.json",{"pre":pre_fs,"post":post_fs});write(evidence/"verifier-results.json",{"pre":pre_v,"post":post_v});write(evidence/"postgres-identity.json",{"pre":pg_pre,"post":pg_post})
    except Exception as exc: result["error"]=f"{type(exc).__name__}: {exc}"
    finally:
        for runtime,label in ((second,"second"),(first,"first")):
            if runtime and runtime.process: runtime.stop(label)
        if second and second.process: result.setdefault("return_codes",{})["second"]=second.process.returncode
        down=subprocess.run(["docker","compose","-p",project,"-f",str(COMPOSE),"down","-v","--remove-orphans"],cwd=ROOT,text=True,capture_output=True);commands.append({"command":"compose down","exit_code":down.returncode,"stdout":down.stdout,"stderr":down.stderr})
        def ids(a): return subprocess.run(a,text=True,capture_output=True).stdout.strip().splitlines()
        cleanup={"containers":ids(["docker","ps","-aq","--filter",f"label=com.docker.compose.project={project}"]),"volumes":ids(["docker","volume","ls","-q","--filter",f"label=com.docker.compose.project={project}"]),"networks":ids(["docker","network","ls","-q","--filter",f"label=com.docker.compose.project={project}"])};shutil.rmtree(temp,ignore_errors=True);cleanup["temporary_directory_removed"]=not temp.exists()
        result["cleanup"]=cleanup;write(evidence/"process-lifecycle.json",result.get("pids",{}));write(evidence/"commands.log",commands);write(evidence/"cleanup.json",cleanup);write(evidence/"restart-result.json",result);(evidence/"backend-first.log").touch(exist_ok=True);(evidence/"backend-second.log").touch(exist_ok=True);sums(evidence)
    print(evidence);return 0 if result["status"].startswith("R9_1_") and not cleanup["containers"]+cleanup["volumes"]+cleanup["networks"] else 1
if __name__=="__main__": raise SystemExit(main())
