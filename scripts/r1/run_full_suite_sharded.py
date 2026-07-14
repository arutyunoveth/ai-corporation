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
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--shards",type=int,default=8);p.add_argument("--shard",type=int);p.add_argument("--prepare",action="store_true");p.add_argument("--aggregate",action="store_true");a=p.parse_args();root=a.output;py=sys.executable
 if a.prepare:
  ids,c=nodeids(py);root.mkdir(parents=True,exist_ok=True);(root/'collected_tests.txt').write_text('\n'.join(ids)+'\n');(root/'collection_stdout.log').write_text(c.stdout);(root/'collection_stderr.log').write_text(c.stderr)
  shards=[ids[i::a.shards] for i in range(a.shards)]
  for i,items in enumerate(shards,1): d=root/f"shard-{i:02d}";d.mkdir(exist_ok=True);(d/'nodeids.txt').write_text('\n'.join(items)+'\n')
  manifest={"collected_count":len(ids),"unique_count":len(set(ids)),"shards":a.shards,"python_version":sys.version,"platform":platform.platform()}
  (root/'collection_manifest.json').write_text(json.dumps(manifest,indent=2))
  plan={"shards":[{"shard":i,"nodeids":items} for i,items in enumerate(shards,1)]}
  (root/'shard_plan.json').write_text(json.dumps(plan,indent=2));return
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
  ids=(root/'collected_tests.txt').read_text().splitlines();plan=json.loads((root/'shard_plan.json').read_text());expected={x['shard']:x['nodeids'] for x in plan['shards']}; results={int(x.parent.name.split('-')[-1]):json.loads(x.read_text()) for x in root.glob('shard-*/result.json')}
  missing_shards=sorted(set(expected)-set(results)); incomplete=sorted(i for i,r in results.items() if not r.get('result_complete'))
  terminal=[n for i,r in results.items() if i in expected and r.get('result_complete') for n in r.get('terminal_nodeids',[])]; scheduled=[n for nodes in expected.values() for n in nodes]
  duplicates=sorted({n for n in terminal if terminal.count(n)>1}); missing=sorted(set(ids)-set(terminal)); unexpected=sorted(set(terminal)-set(ids))
  passed=sum(r.get('passed',0) for r in results.values());skipped=sum(r.get('skipped',0) for r in results.values())
  ok=not (missing_shards or incomplete or missing or unexpected or duplicates) and len(ids)==len(scheduled)==len(terminal)==len(set(terminal)) and all(r['exit_code']==0 for r in results.values())
  result={"status":"passed" if ok else "invalid","reason":None if ok else "incomplete_node_execution","collected_count":len(ids),"scheduled_count":len(scheduled),"shard_assigned_count":len(scheduled),"executed_count":len(terminal),"unique_executed_count":len(set(terminal)),"missing_nodeids":missing,"unexpected_nodeids":unexpected,"duplicate_nodeids":duplicates,"missing_shards":missing_shards,"incomplete_shards":incomplete,"passed":passed,"skipped":skipped,"crashed_shards":[i for i,r in results.items() if not r.get('summary_present')],"nonzero_exit_shards":[i for i,r in results.items() if r['exit_code']!=0]}
  (root/'aggregate_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));
if __name__=='__main__': main()
