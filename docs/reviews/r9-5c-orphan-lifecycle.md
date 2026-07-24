# R9.5C orphan generation and review/lifecycle hardening

Status: `R9_5C_ORPHAN_AND_LIFECYCLE_SOURCE_CI_AND_EVIDENCE_ALIGNED`.

Source/evidence commit: `c15e5cea583f0e7553b35b91d7e719c37bfaebea`.

CI evidence: `output/r9-orphan-lifecycle-20260724T161101Z` from workflow run `30107919148`, artifact `r9-operational-hardening-evidence-c15e5cea583f0e7553b35b91d7e719c37bfaebea` (artifact digest `sha256:6d93af5ad3ff6942961961a79965561115174fd75a837f26eaee5f47b6c29b43`).

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

## Final evidence

The CI runtime completed in 27.78 seconds with status `R9_5C_ORPHAN_AND_LIFECYCLE_FAIL_CLOSED`:

- 8 scenarios, 8 safe and 0 unsafe;
- canonical and artifact filesystem-only orphans were neither imported nor deleted;
- invalid, stale, needs-reanalysis and tampered-artifact states did not advance lifecycle;
- the valid current artifact/review path reached `client_ready` and then `delivered`;
- cleanup complete with no remaining Compose containers, networks or volumes;
- hygiene PASS with no hits;
- exactly 9 evidence files covered by 9 valid `SHA256SUMS` entries.

Workflow run `30107919148` completed all five CI jobs successfully; quality completed both `make check` and the full `make test` suite. No automatic repair, orphan deletion, review mutation, model change or migration was introduced.
