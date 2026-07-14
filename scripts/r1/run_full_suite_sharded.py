#!/usr/bin/env python3
"""Evidence-producing, deterministic pytest sharder for R1 runtime limits."""
from __future__ import annotations
import argparse, hashlib, json, os, platform, re, subprocess, sys, time
from pathlib import Path

NODE = re.compile(r"^tests/.+::.+$")

def run(cmd, **kwargs): return subprocess.run(cmd, text=True, **kwargs)
def nodeids(py):
    p=run([py,"-m","pytest","--collect-only","-q"],capture_output=True)
    ids=[x.strip() for x in p.stdout.splitlines() if NODE.match(x.strip())]
    if p.returncode or not ids or len(ids)!=len(set(ids)): raise RuntimeError(f"collection invalid: exit={p.returncode}, count={len(ids)}, unique={len(set(ids))}")
    return ids,p
def summary(text):
    m=re.search(r"(\d+) passed(?:, (\d+) skipped)?",text)
    return {"summary_present":bool(m),"passed":int(m.group(1)) if m else 0,"skipped":int(m.group(2) or 0) if m else 0}
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--result",type=Path);p.add_argument("--tested-commit-sha");p.add_argument("--tested-tree-sha");p.add_argument("--expected-remote-sha");p.add_argument("--remote-ref",default="origin/codex/r1-b5-release-acceptance");p.add_argument("--shards",type=int,default=8);p.add_argument("--shard",type=int);p.add_argument("--prepare",action="store_true");p.add_argument("--aggregate",action="store_true");a=p.parse_args();root=a.output;py=sys.executable
 if (a.prepare or a.shard or (a.aggregate and (a.output/'shard_plan.json').exists())) and not all((a.tested_commit_sha,a.tested_tree_sha,a.expected_remote_sha)):
  print(json.dumps({'status':'invalid','reason_code':'missing_binding_arguments'})); return 2
 if a.prepare:
  from full_suite_binding import build_execution_binding
  b=build_execution_binding(cwd=Path.cwd(),tested_commit=a.tested_commit_sha,tested_tree=a.tested_tree_sha,expected_remote=a.expected_remote_sha,remote_ref=a.remote_ref,runner=Path(__file__),verifier=Path(__file__).with_name('verify_full_suite_aggregate.py'))
  from full_suite_binding import atomic_write_json, sha256_file
  root.mkdir(parents=True,exist_ok=True); atomic_write_json(root/'execution_binding.json',b)
  if b['status']!='PASS': print(json.dumps(b)); return 2
 if a.prepare:
  ids,c=nodeids(py);root.mkdir(parents=True,exist_ok=True);(root/'collected_tests.txt').write_text('\n'.join(ids)+'\n');(root/'collection_stdout.log').write_text(c.stdout);(root/'collection_stderr.log').write_text(c.stderr)
  shards=[ids[i::a.shards] for i in range(a.shards)]
  for i,items in enumerate(shards,1): d=root/f"shard-{i:02d}";d.mkdir(exist_ok=True);(d/'nodeids.txt').write_text('\n'.join(items)+'\n')
  binding_sha=sha256_file(root/'execution_binding.json')
  metadata={"schema_version":"1.0","runtime_format_version":"3.0","run_id":root.name,"repository_identity":b.get('repository_identity'),"branch":b.get('branch'),"remote_ref":a.remote_ref,"tested_commit_sha":a.tested_commit_sha,"tested_tree_sha":a.tested_tree_sha,"expected_remote_sha":a.expected_remote_sha,"main_sha":None,"execution_binding_path":"execution_binding.json","execution_binding_sha256":binding_sha,"runner_path":str(Path(__file__)) ,"runner_sha256":sha256_file(Path(__file__)),"verifier_path":str(Path(__file__).with_name('verify_full_suite_aggregate.py')),"verifier_sha256":sha256_file(Path(__file__).with_name('verify_full_suite_aggregate.py')),"python_version":sys.version,"pytest_version":None,"created_at":time.time(),"status":"PASS"}
  atomic_write_json(root/'run_metadata.json',metadata); metadata_sha=sha256_file(root/'run_metadata.json')
  manifest={"schema_version":"1.0","runtime_format_version":"3.0","run_id":root.name,"tested_commit_sha":a.tested_commit_sha,"tested_tree_sha":a.tested_tree_sha,"expected_remote_sha":a.expected_remote_sha,"execution_binding_sha256":binding_sha,"run_metadata_sha256":metadata_sha,"runner_sha256":sha256_file(Path(__file__)),"verifier_sha256":sha256_file(Path(__file__).with_name('verify_full_suite_aggregate.py')),"ordered_nodeids":ids,"collected_count":len(ids),"unique_count":len(set(ids)),"node_set_sha256":hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest(),"collection_command":[py,"-m","pytest","--collect-only","-q"],"collection_exit_code":c.returncode,"collection_stdout_path":"collection_stdout.log","collection_stdout_sha256":digest(root/'collection_stdout.log'),"collection_stderr_path":"collection_stderr.log","collection_stderr_sha256":digest(root/'collection_stderr.log'),"created_at":time.time(),"status":"PASS"}
  atomic_write_json(root/'collection_manifest.json',manifest); collection_sha=sha256_file(root/'collection_manifest.json')
  plan={"schema_version":"1.0","runtime_format_version":"3.0","run_id":root.name,"tested_commit_sha":a.tested_commit_sha,"tested_tree_sha":a.tested_tree_sha,"expected_remote_sha":a.expected_remote_sha,"execution_binding_sha256":binding_sha,"run_metadata_sha256":metadata_sha,"collection_manifest_sha256":collection_sha,"node_set_sha256":manifest['node_set_sha256'],"runner_sha256":sha256_file(Path(__file__)),"verifier_sha256":sha256_file(Path(__file__).with_name('verify_full_suite_aggregate.py')),"planner_version":"1.0","planning_parameters":{"shards":a.shards},"expected_shard_ids":list(range(1,a.shards+1)),"shards":[{"shard_id":i,"ordered_nodeids":items,"node_count":len(items)} for i,items in enumerate(shards,1)],"total_assigned_count":len(ids),"created_at":time.time(),"status":"PASS"}
  for item in plan['shards']:
   item['shard']=item['shard_id']; item['nodeids']=item['ordered_nodeids']
  atomic_write_json(root/'shard_plan.json',plan);return
 if a.shard:
  d=root/f"shard-{a.shard:02d}";ids=(d/'nodeids.txt').read_text().splitlines();start=time.time()
  cmd=["/usr/bin/time","-l",py,"-m","pytest","-q","--tb=short","--durations=50",*ids]
  runtime=d/'runtime';tmp=runtime/'tmp';runs=runtime/'demo-runs';tmp.mkdir(parents=True,exist_ok=True);runs.mkdir(parents=True,exist_ok=True)
  env={**os.environ,"PYTHONFAULTHANDLER":"1","PYTHONUNBUFFERED":"1","TMPDIR":str(tmp),"AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR":str(runs),"R1_TEST_RUN_ID":root.name,"R1_SHARD_ID":str(a.shard)}
  (d/'environment.json').write_text(json.dumps({key:env[key] for key in ("TMPDIR","AI_CORP_TENDER_OPERATOR_DEMO_RUNS_DIR","R1_TEST_RUN_ID","R1_SHARD_ID")},indent=2))
  with (d/'stdout.log').open('w') as out,(d/'stderr.log').open('w') as err: r=run(cmd,stdout=out,stderr=err,env=env)
  text=(d/'stdout.log').read_text(errors='replace');s=summary(text)
  # A pytest summary cannot identify individual node outcomes.  Mark a shard
  # terminal only when its summary accounts for every planned node; otherwise
  # it remains incomplete and aggregate must reject it.
  complete=s['summary_present'] and s['passed']+s['skipped']==len(ids)
  result={"schema_version":"2.0","shard":a.shard,"planned_nodeids":ids,"terminal_nodeids":ids if complete else [],"scheduled_count":len(ids),"exit_code":r.returncode,"duration_seconds":round(time.time()-start,3),**s,"result_complete":complete,"result_status":"passed" if complete and r.returncode==0 else "incomplete","last_nodeid":ids[-1] if ids else None}
  tmp_result=d/'result.json.tmp';tmp_result.write_text(json.dumps(result,indent=2));tmp_result.replace(d/'result.json');print(json.dumps(result));return
 if a.aggregate:
  result_path=a.result or root/'aggregate_result.json'
  if not (root/'shard_plan.json').is_file():
   observed=[]
   for x in root.glob('shard-*/result.json'):
    try: observed.append(json.loads(x.read_text()))
    except json.JSONDecodeError: pass
   collected_count=len((root/'collected_tests.txt').read_text().splitlines()) if (root/'collected_tests.txt').is_file() else None
   executed=sum(r.get('passed',0)+r.get('skipped',0) for r in observed)
   result={"runtime_format_version":None,"detected_runtime_format":"legacy_pre_frozen_plan","required_files":["collection_manifest.json","shard_plan.json"],"missing_required_files":["shard_plan.json"],"malformed_required_files":[],"structural_errors":[{"code":"missing_frozen_shard_plan","path":"shard_plan.json","message":"Exact scheduled and assigned node sets cannot be verified."}],"legacy_runtime_format":True,"exact_accounting_possible":False,"status":"invalid","reason_code":"missing_frozen_shard_plan","missing_nodeids":None,"missing_nodeids_known":False,"exact_missing_nodeids_unavailable_reason":"missing_frozen_shard_plan","collected_count":collected_count,"scheduled_count":collected_count,"executed_count":executed,"unique_executed_count":executed,"count_deficit":(collected_count-executed) if collected_count is not None else None,"exit_code":2}
   result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 2
  ids=(root/'collected_tests.txt').read_text().splitlines();plan=json.loads((root/'shard_plan.json').read_text());expected={x['shard']:x['nodeids'] for x in plan['shards']}; results={int(x.parent.name.split('-')[-1]):json.loads(x.read_text()) for x in root.glob('shard-*/result.json')}
  missing_shards=sorted(set(expected)-set(results)); incomplete=sorted(i for i,r in results.items() if not r.get('result_complete'))
  terminal=[n for i,r in results.items() if i in expected and r.get('result_complete') for n in r.get('terminal_nodeids',[])]; scheduled=[n for nodes in expected.values() for n in nodes]
  duplicates=sorted({n for n in terminal if terminal.count(n)>1}); missing=sorted(set(ids)-set(terminal)); unexpected=sorted(set(terminal)-set(ids))
  passed=sum(r.get('passed',0) for r in results.values());skipped=sum(r.get('skipped',0) for r in results.values())
  ok=not (missing_shards or incomplete or missing or unexpected or duplicates) and len(ids)==len(scheduled)==len(terminal)==len(set(terminal)) and all(r['exit_code']==0 for r in results.values())
  result={"status":"passed" if ok else "invalid","reason":None if ok else "incomplete_node_execution","collected_count":len(ids),"scheduled_count":len(scheduled),"shard_assigned_count":len(scheduled),"executed_count":len(terminal),"unique_executed_count":len(set(terminal)),"missing_nodeids":missing,"unexpected_nodeids":unexpected,"duplicate_nodeids":duplicates,"missing_shards":missing_shards,"incomplete_shards":incomplete,"passed":passed,"skipped":skipped,"crashed_shards":[i for i,r in results.items() if not r.get('summary_present')],"nonzero_exit_shards":[i for i,r in results.items() if r['exit_code']!=0]}
  result_path.write_text(json.dumps(result,indent=2));print(json.dumps(result));return 0 if ok else 2
if __name__=='__main__': raise SystemExit(main())
