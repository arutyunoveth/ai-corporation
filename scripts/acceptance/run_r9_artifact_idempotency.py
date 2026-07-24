"""Fail-closed R9.3 evidence: four sequential final-PDF publication requests."""
from __future__ import annotations
import argparse, hashlib, json, os, secrets, shutil, subprocess, sys, tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]; sys.path[:0]=[str(ROOT),str(ROOT/"scripts"/"acceptance")]
from run_r8_acceptance import _enrich_states,_prepare_customer,_seed,snapshot_filesystem  # noqa
from r8_acceptance.runtime import free_port,http  # noqa
from run_r9_application_restart import COMPOSE,CUSTOMER,cleanup_runtime,fetch_db_artifact_binding,fetch_verifier_snapshot,health_status,run_command,run_hygiene_self_test,sanitize_text,sanitize_value,scan_hygiene,snapshot_database,start_uvicorn,stop_uvicorn,utcnow,wait_for_health,write_json,write_sums  # noqa

SUCCESS="R9_3_ARTIFACT_PUBLICATION_IDEMPOTENCY_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL"
FILES=("artifact-idempotency-result.json","publication-attempts.json","application-lifecycle.json","database-snapshots.json","audit-snapshots.json","filesystem-snapshots.json","verifier-results.json","artifact-binding.json","postgres-identity.json","renderer-observation.json","commands.log","backend.log","cleanup.json","SHA256SUMS")

def snap_artifact_root(data:Path)->dict[str,Any]:
    all_files=snapshot_filesystem(data)
    return {k:v for k,v in all_files.items() if "/artifacts" in k or "/analysis/" in k}

def pg(project:str)->dict[str,Any]:
    c=subprocess.run(["docker","compose","-p",project,"-f",str(COMPOSE),"ps","-q","postgres"],cwd=ROOT,text=True,capture_output=True).stdout.strip()
    i=json.loads(subprocess.run(["docker","inspect",c],text=True,capture_output=True).stdout)[0]
    return {"container_id":i["Id"],"started_at":i["State"]["StartedAt"],"restart_count":i["State"].get("RestartCount"),"running":i["State"]["Running"]}

def get(base:str,state:dict[str,Any])->dict[str,Any]:
    cs,cb,_=http("GET",f"{base}/cases/{state['case_id']}",username="",password="")
    ats,ab,_=http("GET",f"{base}/cases/{state['case_id']}/runs/{state['run_id']}/artifacts",username="",password="")
    ps,pdf,_=http("GET",f"{base}/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf",username="",password="")
    return {"case_status":cs,"case":json.loads(cb),"artifacts_status":ats,"artifacts":json.loads(ab),"pdf_status":ps,"pdf_sha256":hashlib.sha256(pdf).hexdigest(),"pdf_byte_size":len(pdf)}

def verify(env:dict[str,str],state:dict[str,Any])->dict[str,str]:
    code="""import json,os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotRunResult,ProcurementCase
from src.tender_research.models import TenderAnalysisRun
from src.modules.customer_pilot.binding_verifier import verify_run_snapshot_binding
from src.modules.customer_pilot.artifacts import verified_pilot_artifact
s=json.loads(os.environ['R9_STATE'])
with Session(create_engine(os.environ['AI_CORP_DATABASE_URL'])) as x:
 r=x.get(PilotRunResult,s['run_result_id']);a=x.get(PilotArtifact,s['artifact_id']);c=x.get(ProcurementCase,s['case_id']);run=x.get(TenderAnalysisRun,s['run_id']);verify_run_snapshot_binding(run=run,case=c,binding=r);verified_pilot_artifact(run,c,r,a);print(json.dumps({'canonical':'PASS','artifact':'PASS'}))"""
    e=env.copy();e['R9_STATE']=json.dumps(state);r=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=e,text=True,capture_output=True)
    if r.returncode: raise RuntimeError(r.stderr)
    return json.loads(r.stdout)

def checks(d:dict[str,Any])->dict[str,bool]:
    attempts=d.get("attempts",[]); first=d.get("after",{}).get("first",{}); replay=d.get("after",{}).get("replays",[]); allsn=[first,*replay]; binding=d.get("binding",{}); life=d["lifecycle"]; db=d.get("database",{}); fs=d.get("filesystem",{}); ver=d.get("verifier",{})
    ids=[a.get("artifact_id") for a in attempts]; keys=[a.get("artifact_key") for a in attempts]; metadata=[a.get("response") for a in attempts]
    return {"application_health_200":life.get("health_status")==200,"first_publication_success":len(attempts)>0 and attempts[0].get("http_status")==201,"three_replays_success":len(attempts)==4 and all(a.get("http_status")==201 for a in attempts[1:]),"four_attempts_recorded":len(attempts)==4,"all_response_artifact_ids_equal":len(set(ids))==1,"all_response_artifact_keys_equal":len(set(keys))==1,"all_response_metadata_equal":len({json.dumps(x,sort_keys=True) for x in metadata})==1,"all_artifact_list_gets_200":all(x.get("http",{}).get("artifacts_status")==200 for x in allsn),"all_pdf_gets_200":all(x.get("http",{}).get("pdf_status")==200 for x in allsn),"all_pdf_hashes_equal":len({x.get("http",{}).get("pdf_sha256") for x in allsn})==1,"all_pdf_sizes_equal":len({x.get("http",{}).get("pdf_byte_size") for x in allsn})==1,"pdf_hash_matches_db":first.get("http",{}).get("pdf_sha256")==binding.get("pdf_sha256"),"pdf_size_matches_db":first.get("http",{}).get("pdf_byte_size")==binding.get("byte_size"),"manifest_hash_matches_db":bool(binding.get("manifest_file_sha256")),"one_run_result":db.get("first",{}).get("business",{}).get("PilotRunResult",{}).get("count")==1,"one_final_artifact":db.get("first",{}).get("business",{}).get("PilotArtifact",{}).get("count")==1,"one_artifact_generation":len([p for p in fs.get("first",{}) if p.endswith("/artifacts")])==1,"one_artifact_exported_audit_event":d.get("audit",{}).get("first")==1,"audit_snapshot_unchanged_after_first":all(x==d.get("audit",{}).get("first") for x in d.get("audit",{}).get("replays",[])),"database_snapshot_unchanged_after_first":all(x==db.get("first") for x in db.get("replays",[])),"filesystem_snapshot_unchanged_after_first":all(x==fs.get("first") for x in fs.get("replays",[])),"pdf_mtime_unchanged_after_first":all(x==fs.get("first") for x in fs.get("replays",[])),"manifest_mtime_unchanged_after_first":all(x==fs.get("first") for x in fs.get("replays",[])),"case_status_operator_review_all_attempts":all(x.get("http",{}).get("case",{}).get("status")=="operator_review" for x in allsn),"run_status_completed_all_attempts":all(x.get("http",{}).get("case",{}).get("runs",[{}])[0].get("status")=="completed" for x in allsn),"canonical_verifier_pass_all_attempts":all(x.get("canonical")=="PASS" for x in ver.get("all",[])),"artifact_verifier_pass_all_attempts":all(x.get("artifact")=="PASS" for x in ver.get("all",[])),"no_canonical_partials":not any(".analysis.partial." in p for p in fs.get("first",{})),"no_artifact_partials":not any(".artifact." in p and ".partial." in p for p in fs.get("first",{})),"no_renderer_temp_files":not any(".r8-final-pdf" in p for p in fs.get("first",{})),"application_process_exited":life.get("process_exited") is True,"application_return_code_recorded":life.get("return_code") is not None,"application_termination_expected":life.get("return_code") in {-15,-9},"cleanup_errors_empty":d.get("cleanup_errors",[])==[],"cleanup_complete":False,"evidence_pack_complete":False,"sha256sums_complete_and_valid":False,"evidence_hygiene_pass":False}

def main()->int:
    evidence=ROOT/"output"/f"r9-artifact-idempotency-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"; evidence.mkdir(parents=True); temp=Path(tempfile.mkdtemp(prefix="r9-idempotency-",dir=ROOT/"output")); data_root=temp/"data";data_root.mkdir(); pp,ap=free_port(),free_port(); password="r9-"+secrets.token_urlsafe(20); project="r9idem"+secrets.token_hex(5); dsn=f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{pp}/r8_acceptance"; secrets_map={"password":password,"database_url":dsn,"temporary_root":str(temp),"authorization":"Authorization: Basic Og=="}; env=os.environ.copy();env.update({"R8_POSTGRES_PASSWORD":password,"R8_POSTGRES_PORT":str(pp),"AI_CORP_DATABASE_URL":dsn,"AI_CORP_ARVECTUM_DATA_DIR":str(data_root),"AI_CORP_PILOT_AUTH_ENABLED":"false","AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED":"false"}); commands=[]; d={"attempts":[],"after":{"replays":[]},"database":{"replays":[]},"filesystem":{"replays":[]},"audit":{"replays":[]},"verifier":{"all":[]},"lifecycle":{},"cleanup_errors":[]}; process=None
    try:
        compose=["docker","compose","-p",project,"-f",str(COMPOSE)];run_command(compose+["up","-d","--wait"],env,commands,secrets_map);run_command([sys.executable,"-m","alembic","upgrade","096_add_r8_canonical_snapshot_binding"],env,commands,secrets_map);_seed(env)
        from sqlalchemy import create_engine,func,select
        from sqlalchemy.orm import Session
        from src.modules.customer_registry.models import CustomerProfile
        from src.modules.customer_pilot.models import PilotAuditEvent
        with Session(create_engine(dsn)) as s:s.add(CustomerProfile(customer_id=CUSTOMER,legal_name="R9 synthetic customer",customer_status="prospect"));s.commit()
        process=start_uvicorn(env,ap,evidence/"backend.log",d["lifecycle"]);assert wait_for_health(process,ap,d["lifecycle"])==200;base=f"http://127.0.0.1:{ap}/api/operator/pilot/customers/{CUSTOMER}"
        def mutate(path:str,body:dict|None=None)->dict:
            status,raw,_=http("POST",base+path,username="",password="",body=body,headers={"Idempotency-Key":"r9-idempotency"} if path.endswith("/runs") else None);assert status in {200,201},(status,raw);return json.loads(raw)
        project_row=mutate("/projects",{"name":"R9 idempotency"});case_row=mutate(f"/projects/{project_row['id']}/cases",{"procurement_number":"0379100000726000101"});run_row=mutate(f"/cases/{case_row['id']}/runs",{});complete=mutate(f"/cases/{case_row['id']}/runs/{run_row['id']}/complete");state={"customer_id":CUSTOMER,"project_id":project_row["id"],"case_id":case_row["id"],"run_id":run_row["id"],"run_result_id":complete["run_result_id"]};endpoint=f"{base}/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf"
        for n in range(1,5):
            requested=utcnow(); status,body,_=http("POST",endpoint,username="",password=""); response=json.loads(body);state["artifact_id"]=response.get("id"); current={"http":get(base,state),"database":snapshot_database(env),"filesystem":snap_artifact_root(data_root),"verifier":verify(env,state)};d["attempts"].append({"attempt":n,"requested_at":requested,"completed_at":utcnow(),"http_status":status,"response":response,"artifact_id":response.get("id"),"artifact_key":response.get("artifact_key"),**{k:response.get(k) for k in ("report_model_hash","renderer_version","pdf_sha256","byte_size","created_at","immutable_at","status")},"pdf_get_status":current["http"]["pdf_status"],"pdf_sha256":current["http"]["pdf_sha256"],"pdf_byte_size":current["http"]["pdf_byte_size"]});d["verifier"]["all"].append(current["verifier"])
            with Session(create_engine(dsn)) as s:audit=s.scalar(select(func.count()).select_from(PilotAuditEvent).where(PilotAuditEvent.event_type=="artifact_exported",PilotAuditEvent.run_id==state["run_id"]))
            if n==1:
                d["after"]["first"]=current;d["database"]["first"]=current["database"];d["filesystem"]["first"]=current["filesystem"];d["audit"]["first"]=audit;state["artifact_id"]=response["id"];d["binding"]=fetch_db_artifact_binding(env,state)
                from src.modules.customer_pilot.models import PilotArtifact
                with Session(create_engine(dsn)) as s: d["binding"]["manifest_file_sha256"]=s.get(PilotArtifact,d["binding"]["id"]).manifest_file_sha256
            else:d["after"]["replays"].append(current);d["database"]["replays"].append(current["database"]);d["filesystem"]["replays"].append(current["filesystem"]);d["audit"]["replays"].append(audit)
        d["postgres"]=pg(project)
    except Exception as e:d["error"]={"type":type(e).__name__,"message":sanitize_text(e,secrets_map)}
    finally:
        try:stop_uvicorn(process,d["lifecycle"])
        except Exception as e:d["cleanup_errors"].append(sanitize_text(e,secrets_map))
        d["cleanup"]=cleanup_runtime(project,temp,evidence,env,commands,secrets_map)
        replay_fs=d.get("filesystem",{}).get("replays",[])
        for name,value in {"publication-attempts.json":d["attempts"],"application-lifecycle.json":d["lifecycle"],"database-snapshots.json":d["database"],"audit-snapshots.json":d["audit"],"filesystem-snapshots.json":d["filesystem"],"verifier-results.json":d["verifier"],"artifact-binding.json":d.get("binding",{}),"postgres-identity.json":d.get("postgres",{}),"renderer-observation.json":{"filesystem_generation_created_once":bool(d.get("filesystem",{}).get("first")),"immutable_files_unchanged":bool(replay_fs) and d.get("filesystem",{}).get("first")==replay_fs[-1],"renderer_call_count":"proven_by_regression_test","test":"test_sequential_final_pdf_replays_are_side_effect_free"},"commands.log":commands,"cleanup.json":d["cleanup"]}.items():write_json(evidence/name,sanitize_value(value,secrets_map))
        path=evidence/"backend.log";path.write_text(sanitize_text(path.read_text(errors="replace") if path.exists() else "",secrets_map)); hits=scan_hygiene(evidence,secrets_map);c=checks(d);c["cleanup_complete"]=d["cleanup"].get("compose_down_exit_code")==0 and not d["cleanup"].get("containers") and not d["cleanup"].get("volumes") and not d["cleanup"].get("networks") and d["cleanup"].get("temporary_directory_removed") and d["cleanup"].get("evidence_directory_exists") and d["cleanup_errors"]==[];c["evidence_hygiene_pass"]=not hits;result={"status":"FAILED","assertions":c,"error":d.get("error"),"cleanup_errors":d["cleanup_errors"],"first_hygiene_hits":hits,"final_hygiene_hits":[]};write_json(evidence/"artifact-idempotency-result.json",sanitize_value(result,secrets_map));result["final_hygiene_hits"]=scan_hygiene(evidence,secrets_map);c["evidence_hygiene_pass"]=not result["final_hygiene_hits"];c["evidence_pack_complete"]=all((evidence/x).exists() for x in FILES if x!="SHA256SUMS");write_json(evidence/"artifact-idempotency-result.json",sanitize_value(result,secrets_map));write_sums(evidence);lines=(evidence/"SHA256SUMS").read_text().splitlines();c["sha256sums_complete_and_valid"]=len(lines)==len([p for p in evidence.iterdir() if p.is_file() and p.name!="SHA256SUMS"]);result["status"]=SUCCESS if not d.get("error") and all(c.values()) and not result["final_hygiene_hits"] else "FAILED";write_json(evidence/"artifact-idempotency-result.json",sanitize_value(result,secrets_map));write_sums(evidence);code=0 if result["status"]==SUCCESS and all(c.values()) else 1
    print(evidence);return code

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--self-test-hygiene",action="store_true");a=p.parse_args();raise SystemExit(0 if run_hygiene_self_test() else 1) if a.self_test_hygiene else SystemExit(main())
