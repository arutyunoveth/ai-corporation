#!/usr/bin/env python3
"""Evidence-producing, deterministic pytest sharder for R1 runtime limits."""
from __future__ import annotations
import argparse, json, platform, re, subprocess, sys, time
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
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--shards",type=int,default=8);p.add_argument("--shard",type=int);p.add_argument("--prepare",action="store_true");p.add_argument("--aggregate",action="store_true");a=p.parse_args();root=a.output;py=sys.executable
 if a.prepare:
  ids,c=nodeids(py);root.mkdir(parents=True,exist_ok=True);(root/'collected_tests.txt').write_text('\n'.join(ids)+'\n');(root/'collection_stdout.log').write_text(c.stdout);(root/'collection_stderr.log').write_text(c.stderr)
  shards=[ids[i::a.shards] for i in range(a.shards)]
  for i,items in enumerate(shards,1): d=root/f"shard-{i:02d}";d.mkdir(exist_ok=True);(d/'nodeids.txt').write_text('\n'.join(items)+'\n')
  (root/'collection_manifest.json').write_text(json.dumps({"collected_count":len(ids),"unique_count":len(set(ids)),"shards":a.shards,"python_version":sys.version,"platform":platform.platform()},indent=2));return
 if a.shard:
  d=root/f"shard-{a.shard:02d}";ids=(d/'nodeids.txt').read_text().splitlines();start=time.time()
  cmd=["/usr/bin/time","-l",py,"-m","pytest","-q","--tb=short","--durations=50",*ids]
  with (d/'stdout.log').open('w') as out,(d/'stderr.log').open('w') as err: r=run(cmd,stdout=out,stderr=err,env={**__import__('os').environ,"PYTHONFAULTHANDLER":"1","PYTHONUNBUFFERED":"1"})
  text=(d/'stdout.log').read_text(errors='replace');result={"shard":a.shard,"scheduled_count":len(ids),"exit_code":r.returncode,"duration_seconds":round(time.time()-start,3),**summary(text),"last_nodeid":ids[-1] if ids else None}
  (d/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return
 if a.aggregate:
  ids=(root/'collected_tests.txt').read_text().splitlines();results=[json.loads(x.read_text()) for x in sorted(root.glob('shard-*/result.json'))];scheduled=[n for d in sorted(root.glob('shard-*/nodeids.txt')) for n in d.read_text().splitlines()]
  ok=len(results)>0 and all(r['exit_code']==0 and r['summary_present'] for r in results)
  result={"status":"passed" if ok and set(ids)==set(scheduled) and len(scheduled)==len(set(scheduled)) else "incomplete","collected_count":len(ids),"scheduled_count":len(scheduled),"executed_count":sum(r['passed']+r['skipped'] for r in results),"unique_executed_count":sum(r['passed']+r['skipped'] for r in results),"missing_nodeids":sorted(set(ids)-set(scheduled)),"duplicate_nodeids":sorted({n for n in scheduled if scheduled.count(n)>1}),"passed":sum(r['passed'] for r in results),"skipped":sum(r['skipped'] for r in results),"crashed_shards":[r['shard'] for r in results if not r['summary_present']],"nonzero_exit_shards":[r['shard'] for r in results if r['exit_code']!=0]}
  (root/'aggregate_result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));
if __name__=='__main__': main()
