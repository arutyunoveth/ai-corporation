# R9.5A interrupted publication boundaries

Status: `R9_5_INTERRUPTED_PUBLICATION_BOUNDARIES_CHARACTERIZED_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL`

Evidence: `output/r9-interrupted-publication-20260724T101225Z`.

The disposable run took 32.10 seconds, used Compose project `r9int426d3aab` and PostgreSQL port `61032`. It recorded an 8-point canonical matrix, a 6-point artifact matrix, five hard-kill scenarios, five faulted processes exiting 97, healthy clean processes with orderly exits, six fresh verifier subprocesses, 24/24 assertions, hygiene success, error-free cleanup, and a valid 16-entry SHA256SUMS. Containers, networks, volumes, and the temporary root were absent after cleanup.

- Canonical pre-rename: no final analysis existed after the kill; a server-shaped partial existed. Retry returned 200, removed the partial, and left one binding and final analysis directory.
- Canonical post-rename: final analysis existed without a DB binding. Retry returned 200 and reused immutable bytes and mtimes unchanged.
- Artifact pre-rename: no final generation, PilotArtifact, or `artifact_exported` event existed; a partial existed. Retry returned 201 and produced one generation, DB row, and audit event.
- Artifact post-rename, same bytes: a filesystem generation existed without DB/audit. Retry returned 201 and replay 201, without changing hashes, sizes, or mtimes.
- Artifact post-rename, conflicting bytes: generation A remained filesystem-only; retry B returned a safe 409 without PilotArtifact or `artifact_exported`. A was unchanged and B was absent from DB, manifest, and filesystem. Classification: `filesystem_only_orphan_conflicting_retry`.

`canonical.after_temp_created` may leave a server-shaped partial; the next normal publish removes it. This requires no production repair: no immutable final exists and ownership is never imported from filesystem. Automatic orphan repair is not implemented, filesystem ownership is not imported into DB, conflicting orphans are not deleted, and general DB/filesystem reconciliation remains the next stage.
