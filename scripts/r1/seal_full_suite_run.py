#!/usr/bin/env python3
"""Seal immutable exact-suite metadata after independent PASS results."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from full_suite_binding import atomic_write_json, sha256_file

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); root=a.output
    aggregate=root/'aggregate_result.json'; verification=root/'verification_result.json'
    if not aggregate.is_file() or not verification.is_file(): return 2
    if json.loads(aggregate.read_text()).get('status') not in ('passed','PASS') or json.loads(verification.read_text()).get('overall_status') not in ('passed','PASS'):
        return 2
    names=['execution_binding.json','run_metadata.json','collection_manifest.json','shard_plan.json']
    names += [str(x.relative_to(root)) for x in sorted(root.glob('shard-*/result.json'))]
    names += ['aggregate_result.json','verification_result.json']
    entries=[]
    for name in names:
        path=root/name
        if not path.is_file(): return 2
        entries.append({'logical_name':name,'relative_path':name,'size':path.stat().st_size,'sha256':sha256_file(path)})
    manifest={'schema_version':'1.0','runtime_format_version':'3.0','entries':entries,'status':'SEALED'}
    atomic_write_json(root/'integrity_manifest.json',manifest)
    lines=[f"{e['sha256']}  {e['relative_path']}" for e in entries]+[f"{sha256_file(root/'integrity_manifest.json')}  integrity_manifest.json"]
    (root/'integrity.sha256').write_text('\n'.join(lines)+'\n')
    return 0
if __name__=='__main__': raise SystemExit(main())
