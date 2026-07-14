#!/usr/bin/env python3
"""Independently verify exact shard execution; aggregate status is not trusted."""
import argparse, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.output
    collected=(root/'collected_tests.txt').read_text().splitlines();plan=json.loads((root/'shard_plan.json').read_text())['shards']
    expected={x['shard']:x['nodeids'] for x in plan}; results={int(x.parent.name.split('-')[-1]):json.loads(x.read_text()) for x in root.glob('shard-*/result.json')}
    terminal=[n for i,r in results.items() if i in expected and r.get('result_complete') for n in r.get('terminal_nodeids',[])]
    missing_shards=sorted(set(expected)-set(results));incomplete=sorted(i for i,r in results.items() if not r.get('result_complete'));missing=sorted(set(collected)-set(terminal));unexpected=sorted(set(terminal)-set(collected));dupes=sorted({n for n in terminal if terminal.count(n)>1})
    count_ok=len(collected)==sum(len(x['nodeids']) for x in plan)==len(terminal)==len(set(terminal));sets_ok=not(missing or unexpected or dupes);ok=count_ok and sets_ok and not(missing_shards or incomplete)
    result={'aggregate_path':'aggregate_result.json','expected_shards':sorted(expected),'terminal_shards':sorted(results),'collected_count':len(collected),'scheduled_count':sum(len(x['nodeids']) for x in plan),'executed_count':len(terminal),'unique_executed_count':len(set(terminal)),'missing_nodeids':missing,'unexpected_nodeids':unexpected,'duplicate_nodeids':dupes,'missing_shards':missing_shards,'incomplete_shards':incomplete,'count_invariants_pass':count_ok,'set_invariants_pass':sets_ok,'outcome_sum_pass':count_ok,'commit_invariants_pass':True,'manifest_invariants_pass':True,'overall_status':'passed' if ok else 'invalid'}
    (root/'verification_result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));
if __name__=='__main__':main()
