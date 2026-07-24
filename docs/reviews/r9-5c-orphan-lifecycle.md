# R9.5C orphan generation and review/lifecycle hardening

Status: `R9_5C_ORPHAN_AND_LIFECYCLE_REMOTE_AUDIT_CORRECTED_SOURCE_CI_AND_EVIDENCE_ALIGNED`.

Source/evidence commit: `726080a08c7b97f572b12285012667ac6a985921`.

CI evidence: `output/r9-orphan-lifecycle-20260724T193542Z` from workflow run `30120854910`, artifact `r9-operational-hardening-evidence-726080a08c7b97f572b12285012667ac6a985921` (artifact digest `sha256:c7bd35784dec4a5c95410a2739b16171a5c615b15892dbbcd818812109bc800d`).

This stage verifies two orphan states and six review/lifecycle transitions through real customer-pilot HTTP paths against disposable PostgreSQL and filesystem state.

## Final matrix

| Classification | Verified behavior |
| --- | --- |
| `filesystem_only_canonical_orphan` | Two completion retries return 409; no `PilotRunResult` is recreated; immutable files remain unchanged. |
| `filesystem_only_artifact_orphan` | Two PDF publication retries return 409; no `PilotArtifact` or export audit is created; generation remains unchanged. |
| `approved_review_without_artifact` | Approved review returns 409; no review row appears and the case remains `operator_review`. |
| `needs_reanalysis_blocks_client_ready` | The review is retained, but client-ready returns 409 and lifecycle does not advance. |
| `tampered_artifact_blocks_client_ready` | Review may already exist, but altered PDF bytes make client-ready return 409. |
| `stale_review_blocks_client_ready` | A review for the superseded run cannot advance the new current run. |
| `delivered_requires_client_ready` | Direct `operator_review -> delivered` transition returns 409. |
| `verified_happy_path` | Verified artifact and approved review allow `client_ready` and then `delivered`. |

## Remote audit correction

The post-completion source audit found that filesystem-only final-PDF rejection previously depended on the renderer producing different volatile bytes. A deterministic renderer could reproduce the existing orphan bytes and the publisher would create a new `PilotArtifact` binding from filesystem state.

The publication/binding boundary is now serialized with a PostgreSQL row lock after rendering. A concurrent committed artifact is verified and compared with the candidate hash and size; identical concurrent publication remains idempotent, conflicting bytes return 409, and an idempotently verified filesystem generation with no DB row is explicitly rejected with 409. A deterministic regression test deletes the DB artifact row, preserves exact PDF and manifest bytes, retries publication with identical rendered bytes, and proves that no DB row or audit event is recreated and no file hash or mtime changes.

The existing PostgreSQL concurrency suites remain green: identical first-publication bytes retain the established 2x201 contract, while conflicting bytes retain the `{201, 409}` contract.

## Final evidence

The CI runtime completed in 29.26 seconds with status `R9_5C_ORPHAN_AND_LIFECYCLE_FAIL_CLOSED`:

- 8 scenarios, 8 safe and 0 unsafe;
- canonical and artifact filesystem-only orphans were neither imported nor deleted;
- invalid, stale, needs-reanalysis and tampered-artifact states did not advance lifecycle;
- the valid current artifact/review path reached `client_ready` and then `delivered`;
- cleanup complete with no remaining Compose containers, networks or volumes;
- hygiene PASS with no hits;
- exactly 9 evidence files covered by 9 valid `SHA256SUMS` entries.

Workflow run `30120854910` completed all five CI jobs successfully. Quality completed `make check` and `make test`; the full suite reported 1679 passed and 188 skipped. No automatic repair, orphan deletion, model change or migration was introduced.