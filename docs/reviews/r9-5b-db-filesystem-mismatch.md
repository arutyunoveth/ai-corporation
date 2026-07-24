# R9.5B DB/filesystem mismatch hardening

Status: `R9_5B_DB_FILESYSTEM_MISMATCH_REMEDIATED_SOURCE_CI_AND_EVIDENCE_ALIGNED`.

Source/evidence commit: `c15e5cea583f0e7553b35b91d7e719c37bfaebea`.

CI evidence: `output/r9-db-filesystem-mismatch-20260724T161034Z` from workflow run `30107919148`, artifact `r9-operational-hardening-evidence-c15e5cea583f0e7553b35b91d7e719c37bfaebea` (artifact digest `sha256:6d93af5ad3ff6942961961a79965561115174fd75a837f26eaee5f47b6c29b43`).

## Initial characterization

Local-only evidence `output/r9-db-filesystem-mismatch-20260724T150508Z` executed eight isolated scenarios and found 7 safe, 1 unsafe, and 0 inconclusive. The unsafe case was `filesystem_only_canonical_snapshot`: a valid immutable snapshot remained on disk after its `PilotRunResult` row was removed, and a repeated completion request returned 200 and recreated the DB binding.

That behavior violated the R9 rule that filesystem presence alone must never establish database ownership.

## Remediation

`bind_completed_analysis(...)` now rejects an idempotently verified canonical snapshot when no DB binding existed before publication. It returns HTTP 409 instead of creating a new `PilotRunResult`. The immutable snapshot remains unchanged and is neither imported nor deleted.

The acceptance runner records real before/mismatch/after/after-retry DB, filesystem and audit snapshots, file hashes, byte sizes and mtimes. It computes created, overwritten and deleted files from those snapshots rather than hard-coding the result. A second tenant with a completed canonical snapshot and final PDF is retained as a sentinel; the run fails if the sentinel DB or filesystem state changes.

## Final matrix

| Classification | HTTP result | Verified outcome |
| --- | ---: | --- |
| `db_only_canonical_binding` | 409 / 409 retry | Missing directory is not recreated; binding remains diagnostic. |
| `filesystem_only_canonical_snapshot` | 409 / 409 retry | No DB binding is created; snapshot is not overwritten or deleted. |
| `incomplete_canonical_snapshot` | 409 / 409 retry | Missing files are not regenerated and existing bytes remain unchanged. |
| `canonical_metadata_mismatch` | 409 / 409 retry | DB metadata and immutable files are not rewritten. |
| `db_only_artifact_generation` | 409 / 409 retry | Missing generation is not recreated from the DB row. |
| `filesystem_only_artifact_generation` | 409 / 409 retry | No `PilotArtifact` or export audit is created; orphan remains unchanged. |
| `incomplete_artifact_generation` | 409 / 409 retry | Incomplete generation is not completed or deleted. |
| `artifact_metadata_mismatch` | 409 / 409 retry | Artifact metadata and immutable files remain unchanged. |

## Final evidence

The CI runtime completed in 27.02 seconds with status `R9_5B_DB_FILESYSTEM_MISMATCH_FAIL_CLOSED`:

- 8 scenarios, 8 safe, 0 unsafe, 0 inconclusive;
- `automatic_repair_performed=false`;
- `filesystem_ownership_imported=false`;
- `filesystem_ownership_import_scenarios=[]`;
- `orphan_deleted=false`;
- `tenant_mixing_detected=false`;
- sentinel tenant DB and filesystem state unchanged;
- cleanup complete with no remaining Compose containers, networks or volumes;
- hygiene PASS with no hits;
- exactly 10 evidence files covered by 10 valid `SHA256SUMS` entries.

Workflow run `30107919148` completed all five CI jobs successfully; quality completed both `make check` and the full `make test` suite. The complete suite reported 1671 passed and 188 skipped tests. No automatic repair, filesystem ownership import, orphan deletion, model change or migration was introduced.
