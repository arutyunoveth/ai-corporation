# R1.B5 release acceptance — R1 RC1

## Release scope inventory

Base main / merge-base: `bc5194600b9b17bd89b2bc02ce92577708a23c35`. Accepted R1 base: `9ca83c31cce6968ca44858aa5b55434c749c6654`.

- Extraction: DOCX NMCK service-table extraction with deterministic row evidence and no inferred quantities.
- Analysis: source-backed vehicle-maintenance services profile, evidence/coverage, unknown contract and economics guards.
- Report: canonical model feeds Web, DOCX and PDF; compatibility sections preserve goods/upload behaviour.
- Isolation: tender-scoped RAG/evidence/memory, run/cache guardrails.
- Test infrastructure: deterministic exact-node micro-shard runner with shard-local runtime roots.
- Fixtures/docs: public real-source provenance metadata and golden regression tests.

No migrations, dependencies, deployment configuration, public-site, production database or credential changes are included.

## Static release review

The changed production files do not refer to the golden registry number, golden fixture path or a hard-coded row count. They retain null quantity semantics, do not calculate line totals from unit prices, and preserve explicit evidence IDs. Renderers consume the canonical model; compatibility values are structured fields in that model, not renderer-side extraction. No production DB access is introduced.

## Test evidence

The unchanged code accepted in B4.2 has two exact-suite passes on the same node manifest SHA `b88f8f702f427ca337f48b131a62cdeac1dd0bcfbdb0d068c446540e47548b53`: 1,550 nodes, 1,365 passed, 185 skipped, zero failed/missing/duplicate/nonzero shards each.

Runtime manifests:

- `tmp/r1/test-runtime/b4-final-run-1-20260714T151221/aggregate_result.json`
- `tmp/r1/test-runtime/b4-final-run-2-20260714T151412/aggregate_result.json`

## RC status

`AUTO_GATES_PASS_HUMAN_REVIEW_REQUIRED`. The candidate does not authorize production deployment or automatic merge. Human review must confirm the source documents and rendered customer artifacts.

## Rejected prior B5 evidence

The older `b5-e2e-run-*` directories remain untouched and are rejected as incomplete evidence: they lacked the tested-tree digest, complete source-inventory validation, extraction-evaluator output, timing and machine determinism.

## Fresh B5 offline E2E evidence v2

Tested code SHA: `7634780bd6a19735a745f1191513a6bd818164f5`; tested tree: `7d337851d2dfdc679c16735b41173ec0006d4cdf`. Source inventory: `tests/fixtures/golden/0352300080626000109/source_inventory.yaml` (SHA-256 `2d0190d957bafb30f87aff51d7c0efd19e5d5a233f1b31dcaf2147896fced758`).

- Run 1: `tmp/r1/release-candidate/b5-e2e-v2-run-1-20260714T143608263012/end_to_end_result.json` — PASS, SHA-256 `fd712c4db34b4dc0bcf4878c3603f1a1397c9970588736ff4556848dbe745e93`.
- Run 2: `tmp/r1/release-candidate/b5-e2e-v2-run-2-20260714T143608827375/end_to_end_result.json` — PASS, SHA-256 `367eb415966e438bfc007972c7eac90be9f319b53bc3b1b5acf6523cefff4010`.

Each run regenerated extraction, analysis, canonical JSON, HTML, DOCX and PDF; all three evaluator exit codes are zero. Both source validations passed, produced 43/43 service rows with 100% evidence, retained `quantity=null`/`not_specified`, disclosed the missing contract, and returned `needs_review`. `tmp/r1/release-candidate/b5-e2e-v2-determinism.json` is PASS with no unexpected semantic differences. Focused acceptance is `tmp/r1/release-candidate/b5-focused-result.json` (50 collected / 50 passed / 0 failed); secret scan is clean and customer-artifact local-path leakage is zero.

Final B5 status: `B5_E2E_V2_PASS_HUMAN_REREVIEW_REQUIRED`. This does not authorize merge, deploy, tag, or production access.
