# R9.5C orphan generation and review/lifecycle hardening

Status: `R9_5C_ORPHAN_AND_LIFECYCLE_SOURCE_PENDING_CI`.

This stage verifies two orphan states and six review/lifecycle transitions through real customer-pilot HTTP paths against disposable PostgreSQL and filesystem state.

## Matrix

| Classification | Required behavior |
| --- | --- |
| `filesystem_only_canonical_orphan` | Two completion retries return 409; no `PilotRunResult` is recreated; immutable files remain unchanged. |
| `filesystem_only_artifact_orphan` | Two PDF publication retries return 409; no `PilotArtifact` or export audit is created; generation remains unchanged. |
| `approved_review_without_artifact` | Approved review returns 409; no review row appears and the case remains `operator_review`. |
| `needs_reanalysis_blocks_client_ready` | The review is retained, but client-ready returns 409 and lifecycle does not advance. |
| `tampered_artifact_blocks_client_ready` | Review may already exist, but altered PDF bytes make client-ready return 409. |
| `stale_review_blocks_client_ready` | A review for the superseded run cannot advance the new current run. |
| `delivered_requires_client_ready` | Direct `operator_review -> delivered` transition returns 409. |
| `verified_happy_path` | Verified artifact and approved review allow `client_ready` and then `delivered`. |

The acceptance evidence records before/after DB and filesystem state, request responses, audit state, cleanup and checksums. A final run must report eight safe scenarios, zero unsafe scenarios, no orphan import or deletion, and no lifecycle advancement without a verified current review/artifact binding.

No automatic repair, orphan deletion, review mutation, model change or migration is introduced. Runtime evidence is produced by CI and must be attached before this review is final.
