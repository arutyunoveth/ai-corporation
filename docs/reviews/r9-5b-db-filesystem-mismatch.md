# R9.5B DB/filesystem mismatch characterization

Status: `R9_5B_DB_FILESYSTEM_MISMATCH_CHARACTERIZATION_FAIL_CLOSED`.

Local-only runtime evidence: `output/r9-db-filesystem-mismatch-20260724T150508Z`.
The disposable PostgreSQL/Docker runtime completed in 16.05 seconds. It executed eight isolated customer/project/case/run scenarios: 7 safe, 1 unsafe, and 0 inconclusive. No repair, filesystem ownership import by the runner, or orphan deletion was performed.

| Classification | Actual HTTP result | Observed outcome |
| --- | --- | --- |
| `db_only_canonical_binding` | 409, `Existing canonical snapshot is invalid` | The binding remained, the missing immutable directory was not recreated, and an invalid-snapshot audit event was added. |
| `filesystem_only_canonical_snapshot` | 200 | **Unsafe defect:** the existing snapshot directory was accepted and a new DB binding plus completion audit event were created. Files were not overwritten. |
| `incomplete_canonical_snapshot` | 409, `Existing canonical snapshot is invalid` | The incomplete directory and DB binding remained unchanged; diagnostic audit was added. |
| `canonical_metadata_mismatch` | 409, `Existing canonical snapshot is invalid` | Mismatched binding metadata and filesystem stayed unchanged; diagnostic audit was added. |
| `db_only_artifact_generation` | 409, `Final artifact trust binding is invalid` | The DB artifact row remained, the missing generation was not recreated, and audit/filesystem stayed unchanged. |
| `filesystem_only_artifact_generation` | 409, `Immutable final PDF conflicts with this run` | The orphan generation was neither imported nor deleted. |
| `incomplete_artifact_generation` | 409, `Final artifact trust binding is invalid` | The incomplete generation and DB artifact remained unchanged. |
| `artifact_metadata_mismatch` | 409, `Final artifact trust binding is invalid` | The mismatched artifact metadata and generation remained unchanged. |

Every scenario records HTTP operation, before/mismatch/after DB and filesystem snapshots, audit events, overwrite/delete/import indicators, and retry safety in its evidence payload. There was no tenant mixing: all eight runs were distinct. The only detected defect is automatic re-binding of a filesystem-only canonical snapshot; it is deliberately not repaired in this step.

Assertions confirm eight exact classifications, isolated tenants, snapshots, no automatic repair, and no orphan deletion. `no_filesystem_ownership_import` is intentionally false because the unsafe canonical case created the new row. Cleanup passed: Compose down returned 0, no cleanup errors occurred, and the temporary root was removed. Hygiene passed with no hits. `SHA256SUMS` has 10/10 valid entries for the exact evidence set.

Runtime evidence is local only. A subsequent stage must require an explicit policy for the filesystem-only canonical case; this review proposes no repair implementation.
