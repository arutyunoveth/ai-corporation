# R1.B3 — analysis acceptance, 0352300080626000109

## Result

`ANL-001` and `ANL-002` are resolved by a source-backed services analysis path. This change does not modify ingestion, table extraction, or report renderers.

## Root cause

The category detector returned `services`, but `_build_preliminary_procurement_analysis()` had no non-training services profile. It therefore continued through a legacy education-oriented fallback. Separately, the generic non-goods economics fallback contained hard-coded software/integration prompts (including СМЭВ/ЕРН and license-transfer costs). Neither fallback consumed extracted service rows or their evidence.

This was systemic rather than registry-specific: any non-training services procurement could inherit those unrelated assumptions. Earlier tests covered goods, software work and education services, but not a real unit-priced vehicle-maintenance service table.

## Implemented controls

- A deterministic services profile obtains its subject from notice XML, reads OKPD2, and identifies `vehicle_maintenance_services` from general domain signals (OKPD2 `45.20` or vehicle diagnostic/maintenance/repair vocabulary).
- The analysis context now keeps source service rows, stable evidence IDs, `quantity: null`, `quantity_status: not_specified`, units, unit prices, document coverage, missing contract and unknown contractual terms.
- The target profile analyzes every extracted service row and reports extracted/analyzed/ignored/evidence coverage; it does not infer a fixed volume or sum unit prices into contract revenue.
- Risks, questions, economics and recommendation are source-limited: the missing draft contract, absent supplier profile, absent cost inputs and uncertain operating capacity lead to `needs_review`, never an unconditional GO.
- Legacy education services keep their existing documented profile. Software-related profiles remain isolated from vehicle services.
- `scripts/r1/evaluate_golden_analysis.py` adds deterministic gates for category, subject/OKPD2, row coverage, evidence, missing contract, prohibited claims, decision and source completeness.

## Candidate facts and limitations

- Subject: diagnostic, maintenance and current-repair services for motor vehicles.
- Category / OKPD2: `services` / `45.20`.
- Item coverage: 43 extracted, 43 analyzed, 0 ignored; fixed row quantities remain unspecified.
- Known: unit prices and the stated NMCk. Unknown: actual call-off volume, internal cost, materials/parts policy, logistics, supplier capability and project-contract conditions.
- The project contract is absent from the available primary source set. Payment, acceptance, penalties, security and responsibility are therefore explicitly unknown rather than negative findings.

## Verification

Focused run: `56 passed`:

```text
.venv/bin/python -m pytest tests/test_tender_operator_agent_meaningful_analysis.py \
  tests/test_tender_operator_agent_upload_demo.py tests/test_tender_operator_agent_demo.py \
  tests/test_tender_operator_agent_report_export.py tests/r1 -q --tb=short
```

Full deterministic sharded run: `1,548` scheduled/collected/executed unique node IDs; `1,363 passed`, `185 skipped`, no failures, crashes, non-zero shards, missing or duplicated node IDs. Aggregate manifest: `tmp/r1/test-runtime/b3-20260714T142115/aggregate_result.json` (runtime artifact, intentionally not committed).

Commits: `17617e8433b40050f47fa114a20bcb1a9b494b47` (implementation) and the following acceptance-metadata commit. No production database, production ingest, runtime deployment or renderer was used by this stage.
