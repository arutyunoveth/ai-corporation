#!/usr/bin/env python3
"""Independently verify exact shard execution; aggregate status is not trusted."""
import argparse, json, hashlib, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--result',type=Path);a=p.parse_args();root=a.output;result_path=a.result or root/'verification_result.json'
    binding_path=root/'execution_binding.json'
    if binding_path.exists():
        binding=json.loads(binding_path.read_text())
        if binding.get('status')!='PASS':
            result={'verification_class':'execution_binding_invalid','reason_codes':binding.get('reason_codes',[]),'exact_accounting_possible':False,'overall_status':'invalid','exit_code':2};result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 2
    if not (root/'shard_plan.json').is_file():
        collected=len((root/'collected_tests.txt').read_text().splitlines()) if (root/'collected_tests.txt').is_file() else None
        observed=[]
        for x in root.glob('shard-*/result.json'):
            try: observed.append(json.loads(x.read_text()))
            except json.JSONDecodeError: pass
        executed=sum(r.get('passed',0)+r.get('skipped',0) for r in observed)
        result={'verification_class':'structural_invalidity','reason_codes':['missing_frozen_shard_plan'],'legacy_runtime_format':True,'exact_accounting_possible':False,'collected_count':collected,'executed_count':executed,'unique_executed_count':executed,'count_deficit':collected-executed if collected is not None else None,'missing_nodeids':None,'missing_nodeids_known':False,'overall_status':'invalid','exit_code':2}
        result_path.parent.mkdir(parents=True,exist_ok=True);result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 2
    binding=json.loads((root/'execution_binding.json').read_text()) if (root/'execution_binding.json').is_file() else {}
    plan_doc=json.loads((root/'shard_plan.json').read_text()); plan=plan_doc['shards']
    expected_commit=binding.get('tested_commit_sha'); expected_tree=binding.get('tested_tree_sha')
    expected={x['shard']:x['nodeids'] for x in plan}; results={int(x.parent.name.split('-')[-1]):json.loads(x.read_text()) for x in root.glob('shard-*/result.json')}
    terminal=[n for i,r in results.items() if i in expected and r.get('result_complete') for n in r.get('terminal_nodeids',[])]
    missing_shards=sorted(set(expected)-set(results));incomplete=sorted(i for i,r in results.items() if not r.get('result_complete'));missing=sorted(set(collected)-set(terminal));unexpected=sorted(set(terminal)-set(collected));dupes=sorted({n for n in terminal if terminal.count(n)>1})
    count_ok=len(collected)==sum(len(x['nodeids']) for x in plan)==len(terminal)==len(set(terminal));sets_ok=not(missing or unexpected or dupes);ok=count_ok and sets_ok and not(missing_shards or incomplete)
    commits={r.get('tested_commit_sha') for r in results.values()}; trees={r.get('tested_tree_sha') for r in results.values()}
    commit_ok=bool(expected_commit) and commits=={expected_commit}; tree_ok=bool(expected_tree) and trees=={expected_tree}
    result={'aggregate_path':'aggregate_result.json','expected_shards':sorted(expected),'terminal_shards':sorted(results),'collected_count':len(collected),'scheduled_count':sum(len(x['nodeids']) for x in plan),'executed_count':len(terminal),'unique_executed_count':len(set(terminal)),'missing_nodeids':missing,'unexpected_nodeids':unexpected,'duplicate_nodeids':dupes,'missing_shards':missing_shards,'incomplete_shards':incomplete,'count_invariants_pass':count_ok,'set_invariants_pass':sets_ok,'outcome_sum_pass':count_ok,'tested_commit_sha':expected_commit,'tested_tree_sha':expected_tree,'observed_commit_shas':sorted(x for x in commits if x),'observed_tree_shas':sorted(x for x in trees if x),'commit_binding_pass':commit_ok,'tree_binding_pass':tree_ok,'execution_binding_pass':binding.get('status')=='PASS','overall_status':'passed' if ok and commit_ok and tree_ok and binding.get('status')=='PASS' else 'invalid'}
    result_path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 0 if ok else 2
if __name__=='__main__':raise SystemExit(main())
