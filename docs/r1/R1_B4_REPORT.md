# R1.B4 — canonical report, 0352300080626000109

## Root cause

Web used the mutable `outputs` payload directly, while DOCX/PDF independently converted a legacy markdown/HTML view. This split discarded the service catalogue, row evidence and unknown-contract semantics in exports. The old renderer also had no canonical representation for those facts.

## Change

`report_model.py` creates one renderer-neutral canonical model before persistence. It holds the service catalogue, explicit null quantity semantics, unit prices, evidence map, document limits, risks and `needs_review` decision. The persisted `canonical_report.json` is the source for web HTML and the report markdown used by exports. When the canonical artifact is available DOCX/PDF construct their catalogues directly from it; legacy export remains a compatibility fallback.

## Acceptance evidence

- Canonical report: 43 service rows, 43 analyzed, 0 invented line totals.
- Web/DOCX/PDF parity evaluator: PASS.
- Focused report/export tests: PASS.
- Runtime artifacts: `tmp/r1/golden-report/0352300080626000109/`.
- The report explicitly discloses missing draft contract, unknown volume, absent supplier profile and unavailable profitability calculation.

RPT-001 remains open pending a green full-suite run. The first B4 parallel sharded run exposed pre-existing shared runtime-state failures in upload/intake tests; it is not a valid full-suite PASS. Extraction and analysis behavior were not altered.
