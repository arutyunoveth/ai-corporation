# R1.B4.1 suite stabilization

## First failure run

The B4 exact-node sharded run had failures in shards 02, 04–08. All failures were deterministic assertions in upload/intake report tests, not process crashes or resource collisions.

| Failure IDs | Shared suspect | Classification |
|---|---|---|
| upload-demo report sections | canonical web renderer | Product regression |
| getDocs intake report labels | canonical web renderer | Product regression |
| goods catalogue/address/ГОСТ view | canonical web renderer | Product regression |

The canonical renderer replaced legacy presentation but omitted data previously visible to ordinary goods/upload flows: report title and notice metadata, archive/documents controls, preliminary analysis, goods specification detail, quote comparison, economics and contract highlights.

## Correction

Those values are now mapped once into `compatibility_sections` of the canonical model and rendered from that model. No test was skipped or weakened; no global test runtime path, database or environment setting was changed.

## Evidence so far

- All eight original failing nodes pass in individual fresh-process execution.
- Focused B4 report/export tests pass.
- A combined six-shard diagnostic run exceeded the external monolithic command limit before producing a pytest summary; it is not counted as PASS.

## Resumable acceptance

The runner now supplies every shard its own `TMPDIR` and demo-run root. Two frozen 32-micro-shard runs completed on commit `08527c1`: each collected/scheduled/executed 1,550 unique node IDs, with 1,365 passed and 185 skipped; there were no failed, nonzero, crashed, missing or duplicate nodes. Their manifest SHA-256 values match: `b88f8f702f427ca337f48b131a62cdeac1dd0bcfbdb0d068c446540e47548b53`.

Runtime evidence: `tmp/r1/test-runtime/b4-final-run-1-20260714T151221/aggregate_result.json` and `tmp/r1/test-runtime/b4-final-run-2-20260714T151412/aggregate_result.json`.

RPT-001 is resolved, subject to human review of the generated report.
