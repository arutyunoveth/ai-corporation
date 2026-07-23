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
def safe(value, temp=None, password=None, url=None):
    text=str(value).replace(str(ROOT),"<REPOSITORY_ROOT>").replace(str(Path.home()),"<USER_HOME>").replace(sys.executable,"<PROJECT_PYTHON>")
    for secret, replacement in ((url,"<REDACTED_DATABASE_URL>"),(password,"<REDACTED>"),(str(temp) if temp else None,"<TEMP_DATA_ROOT>")):
        if secret: text=text.replace(secret,replacement)
    return text
def hygiene(evidence, password, url, temp):
    forbidden={"password":password,"database_url":url,"repository_root":str(ROOT),"temporary_root":str(temp),"user_home":str(Path.home()),"authorization":"Authorization"}
    hits=[]
    for path in evidence.iterdir():
        if path.is_file() and path.name!="SHA256SUMS":
            raw=path.read_bytes().decode("utf-8","ignore")
            hits += [{"file":path.name,"marker":name} for name, marker in forbidden.items() if marker and marker in raw]
    return hits
def main():
    stamp=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"); evidence=ROOT/"output"/f"r9-application-restart-{stamp}";evidence.mkdir(parents=True)
    temp=Path(tempfile.mkdtemp(prefix="r9-restart-",dir=ROOT/"output"));data=temp/"data";data.mkdir();pg,api=free_port(),free_port();assert pg!=api
    password="r9-"+secrets.token_urlsafe(20);project="r9restart"+secrets.token_hex(5);url=f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{pg}/r8_acceptance"
    env=os.environ.copy();env.update({"R8_POSTGRES_PASSWORD":password,"R8_POSTGRES_PORT":str(pg),"AI_CORP_DATABASE_URL":url,"AI_CORP_ARVECTUM_DATA_DIR":str(data),"AI_CORP_PILOT_AUTH_ENABLED":"false","AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED":"false"})
    commands=[]; first=second=first_process=second_process=None; cleanup={}; result={"status":"FAILED","assertions":{}}; state={}; lifecycle={"first":{},"second":{}}
    try:
        compose=["docker","compose","-p",project,"-f",str(COMPOSE)]; command(compose+["up","-d","--wait"],env,commands); command([sys.executable,"-m","alembic","upgrade","head"],env,commands); assert revision(env,commands)=="096_add_r8_canonical_snapshot_binding"
        _seed(env)
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from src.modules.customer_registry.models import CustomerProfile
        with Session(create_engine(env["AI_CORP_DATABASE_URL"])) as session:
            session.add(CustomerProfile(customer_id=CUSTOMER, legal_name="R9 synthetic customer", customer_status="prospect")); session.commit()
        lifecycle["first"]["start_requested_at"]=now();first=Uvicorn(root=ROOT,env=env,port=api,log=evidence/"backend-first.log");first.start("first");first_process=first.process;lifecycle["first"].update({"pid":first_process.pid,"process_started_at":now()});first.wait_ready("",""); first_health=status(f"http://127.0.0.1:{api}/health"); lifecycle["first"].update({"health_checked_at":now(),"health_status":first_health}); assert first_health==200
        base=f"http://127.0.0.1:{api}/api/operator/pilot/customers/{{customer}}";state=_prepare_customer(base,"","",CUSTOMER);_enrich_states(env,[state])
        case_status,case_body,_=http("GET",base.format(customer=CUSTOMER)+f"/cases/{state['case_id']}",username="",password=""); assert case_status==200 and json.loads(case_body)["status"]=="delivered"
        pdf_url=base.format(customer=CUSTOMER)+f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf";s,pdf,_=http("GET",pdf_url,username="",password="");assert s==200
        pre_db={"business":snapshot_business_db(env),"audit":snapshot_audit(env)};pre_fs=snapshot_filesystem(data);pre_v=verifiers(env,state);pg_pre=pg_identity(project)
        first_pid=first_process.pid;lifecycle["first"]["stop_requested_at"]=now();first.stop("first"); first_return=first_process.returncode;lifecycle["first"].update({"exited_at":now(),"return_code":first_return,"termination_method":"SIGTERM","process_exited":first_process.poll() is not None}); first_unavailable=status(f"http://127.0.0.1:{api}/health"); assert first_unavailable is None
        lifecycle["second"]["start_requested_at"]=now();second=Uvicorn(root=ROOT,env=env,port=api,log=evidence/"backend-second.log");second.start("second");second_process=second.process;lifecycle["second"].update({"pid":second_process.pid,"process_started_at":now()});second.wait_ready("",""); second_health=status(f"http://127.0.0.1:{api}/health");lifecycle["second"].update({"health_checked_at":now(),"health_status":second_health}); assert second_health==200 and second.process.pid!=first_pid
        post_case_status,post_case_body,_=http("GET",base.format(customer=CUSTOMER)+f"/cases/{state['case_id']}",username="",password=""); assert post_case_status==200 and json.loads(post_case_body)["status"]=="delivered"
        artifact_status,artifact_body,_=http("GET",base.format(customer=CUSTOMER)+f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts",username="",password=""); assert artifact_status==200 and len(json.loads(artifact_body))==1
        s,pdf_after,_=http("GET",pdf_url,username="",password="");assert s==200
        post_db={"business":snapshot_business_db(env),"audit":snapshot_audit(env)};post_fs=snapshot_filesystem(data);post_v=verifiers(env,state);pg_post=pg_identity(project)
        second_pid=second.process.pid; assertions={"first_health_200":first_health==200,"second_health_200":second_health==200,"first_health_unavailable_after_stop":first_unavailable is None,"different_pids":second_pid!=first_pid,"first_exited_before_second_started":first_return is not None,"postgres_container_id_unchanged":pg_pre["id"]==pg_post["id"],"postgres_started_at_unchanged":pg_pre["started_at"]==pg_post["started_at"],"postgres_restart_count_unchanged":pg_pre["restart_count"]==pg_post["restart_count"],"alembic_revision_unchanged":revision(env,commands)=="096_add_r8_canonical_snapshot_binding","db_snapshots_equal":pre_db==post_db,"filesystem_snapshots_equal":pre_fs==post_fs,"canonical_verifier_pass_pre_post":pre_v["canonical"]==post_v["canonical"]=="PASS","artifact_verifier_pass_pre_post":pre_v["artifact"]==post_v["artifact"]=="PASS","review_verifier_pass_pre_post":pre_v["review"]==post_v["review"]=="PASS","case_http_identity_preserved":post_case_status==200,"artifact_http_identity_preserved":artifact_status==200,"lifecycle_http_preserved":json.loads(post_case_body)["status"]=="delivered","pdf_bytes_equal":pdf==pdf_after,"pdf_hash_matches_db":hashlib.sha256(pdf).hexdigest()==state["pdf_sha256"],"pdf_size_matches_db":len(pdf)==len(pdf_after),"one_run_result":pre_db["business"]["PilotRunResult"]["count"]==1,"one_final_artifact":pre_db["business"]["PilotArtifact"]["count"]==1,"one_review":pre_db["business"]["PilotReview"]["count"]==1,"no_canonical_partials":not any(".analysis.partial." in p for p in pre_fs),"no_artifact_partials":not any(".artifact." in p and ".partial." in p for p in pre_fs),"audit_count_unchanged":pre_db["audit"]==post_db["audit"]}
        assert all(assertions.values()),assertions;result={"status":"R9_1_APPLICATION_RESTART_SMOKE_PASS_LOCAL_EVIDENCE_CORRECTED","assertions":assertions,"ids":state,"http":{"first_health":first_health,"first_health_after_stop":first_unavailable,"second_health":second_health,"case_post":post_case_status,"artifacts_post":artifact_status,"pdf_pre":200,"pdf_post":s},"pids":{"first":first_pid,"second":second_pid},"return_codes":{"first":first_return},"pdf_sha256":hashlib.sha256(pdf).hexdigest()}
        write(evidence/"database-snapshots.json",{"pre":pre_db,"post":post_db});write(evidence/"filesystem-snapshots.json",{"pre":pre_fs,"post":post_fs});write(evidence/"verifier-results.json",{"pre":pre_v,"post":post_v});write(evidence/"postgres-identity.json",{"pre":pg_pre,"post":pg_post})
    except Exception as exc: result["error"]=f"{type(exc).__name__}: {exc}"
    finally:
        for runtime,label in ((second,"second"),(first,"first")):
            if runtime and runtime.process: runtime.stop(label)
        if second: result.setdefault("return_codes",{})["second"]=second_process.returncode
        down=subprocess.run(["docker","compose","-p",project,"-f",str(COMPOSE),"down","-v","--remove-orphans"],cwd=ROOT,text=True,capture_output=True);commands.append({"command":"compose down","exit_code":down.returncode,"stdout":down.stdout,"stderr":down.stderr})
        def ids(a): return subprocess.run(a,text=True,capture_output=True).stdout.strip().splitlines()
        cleanup={"containers":ids(["docker","ps","-aq","--filter",f"label=com.docker.compose.project={project}"]),"volumes":ids(["docker","volume","ls","-q","--filter",f"label=com.docker.compose.project={project}"]),"networks":ids(["docker","network","ls","-q","--filter",f"label=com.docker.compose.project={project}"])};shutil.rmtree(temp,ignore_errors=True);cleanup["temporary_directory_removed"]=not temp.exists()
        if second_process: lifecycle["second"].update({"stop_requested_at":now(),"exited_at":now(),"return_code":second_process.returncode,"termination_method":"SIGTERM","process_exited":second_process.poll() is not None})
        cleanup_complete=down.returncode==0 and not cleanup["containers"]+cleanup["volumes"]+cleanup["networks"] and cleanup["temporary_directory_removed"] and evidence.exists(); result.setdefault("assertions",{})["both_return_codes_recorded"]=len(result.get("return_codes",{}))==2 and all(v is not None for v in result["return_codes"].values());result["assertions"]["first_exited_before_second_started"]=lifecycle["first"].get("exited_at","")<=lifecycle["second"].get("start_requested_at","");result["assertions"]["process_termination_expected"]=all(x.get("return_code") == -15 for x in lifecycle.values());result["assertions"]["cleanup_complete"]=cleanup_complete; result["cleanup"]=cleanup;write(evidence/"process-lifecycle.json",lifecycle);write(evidence/"commands.log",[{**x,"command":safe(x["command"],temp,password,url),"stdout":safe(x["stdout"],temp,password,url),"stderr":safe(x["stderr"],temp,password,url)} for x in commands]);write(evidence/"cleanup.json",cleanup);(evidence/"backend-first.log").touch(exist_ok=True);(evidence/"backend-second.log").touch(exist_ok=True); result["assertions"]["evidence_hygiene_pass"]=not hygiene(evidence,password,url,temp); result["status"]="R9_1_APPLICATION_RESTART_SMOKE_PASS_LOCAL_FAIL_CLOSED_EVIDENCE" if result.get("status","").startswith("R9_1_") and all(result["assertions"].values()) else "FAILED";write(evidence/"restart-result.json",result);result["assertions"]["evidence_hygiene_pass"]=not hygiene(evidence,password,url,temp);write(evidence/"restart-result.json",result);sums(evidence)
    print(evidence);return 0 if result["status"].startswith("R9_1_") and not cleanup["containers"]+cleanup["volumes"]+cleanup["networks"] else 1
if __name__=="__main__": raise SystemExit(main())
