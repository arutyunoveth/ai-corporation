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

The full two-run sharded acceptance remains pending and RPT-001 remains open.
