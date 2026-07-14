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

## Fresh B5 offline E2E evidence

Tested code SHA: `63e1c68a14576385d2f234395b7b3743d5e0b94c`. Two fresh isolated runs used the preserved real notice XML and NMCK DOCX only; network, production ingest and production DB were not used.

- Run 1: `tmp/r1/release-candidate/b5-e2e-run-1-20260714T163335/end_to_end_result.json`
- Run 2: `tmp/r1/release-candidate/b5-e2e-run-2-20260714T163336/end_to_end_result.json`

Each run regenerated extraction, analysis, canonical JSON, HTML, DOCX and PDF; analysis and report evaluators passed. Both source validations passed, produced 43/43 service rows with full row evidence, retained `quantity=null`/`not_specified`, disclosed the missing contract, and returned `needs_review`. Semantic gates match; binary hashes may differ only because each run has a new runtime ID.
