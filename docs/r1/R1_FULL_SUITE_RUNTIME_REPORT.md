# R1.A2 full-suite runtime verification

## Result

`SHARDED_FULL_SUITE_PASS_MONOLITHIC_RUNTIME_LIMIT`

The current commit under verification is `be09108c643ec61246ba3547e5902838f2d34665`.
No product code was changed for this task. The only new code is the deterministic
test runner at `scripts/r1/run_full_suite_sharded.py`.

## Collection and coverage

- Collected node IDs: 1542.
- Unique collected node IDs: 1542.
- Scheduled node IDs: 1542.
- Executed node IDs: 1542.
- Missing and duplicate node IDs: none.
- Shards: 8 fresh pytest processes, each with an exit code of zero and a pytest
  summary.
- Aggregate: 1357 passed, 185 skipped, zero failed/errors/crashed shards.

The machine-readable evidence is under the directory named by
`tmp/r1/test-runtime/current-run.txt`: `collection_manifest.json`, every
`shard-*/result.json`, and `aggregate_result.json`.

## Monolithic runtime limit

The controlled monolithic invocation used `PYTHONFAULTHANDLER=1`,
`PYTHONUNBUFFERED=1`, `/usr/bin/time -l`, `--durations=50`, and `--tb=short`.
It consistently stopped around the external 30-second execution boundary after
about 32% of test output, without a pytest summary or a normal pytest failure.
The same effect occurred in a combined R1/RAG/Hermes/registry run at 82%.

This is not a regression from `be09108`: the exact complete node set passes in
fresh isolated processes, including the previously suspect RAG/registry region.
The RAG + registry focused sequence passed 33 tests; R1/RAG/Hermes focused
coverage passed 36 tests before the sharded verification.

## Environment and security evidence

Environment and collection files are in `tmp/r1/test-runtime/baseline/`.
The existing secret scanner completed with `secret scan: clean`.
No production database or runtime was used.

## Decision

The ordinary monolithic status is not claimed as a pass because the external
runtime boundary prevents its completion. The sharded result is complete and
evidence-backed; transition to stage B is permitted by the R1.A2 acceptance
variant for a confirmed monolithic runtime limit.
