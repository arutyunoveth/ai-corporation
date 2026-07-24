# R9.5A interrupted publication boundaries

Status: `R9_5_INTERRUPTED_PUBLICATION_BOUNDARIES_CHARACTERIZED_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL`

Evidence: `output/r9-interrupted-publication-20260724T105027Z`.

The disposable local run took 32.64 seconds. It recorded an 8-point canonical matrix, a 6-point artifact matrix, five hard-kill scenarios, and 65/65 passing assertions. All five faulted processes exited 97; each clean process returned health 200 and exited cleanly. The final hygiene scan passed with `hits: []`; the real hygiene negative self-test and real failure-finalization negative self-test both passed.

Six fresh verifier subprocesses passed with exact expected/actual identities: two canonical, three persisted-artifact, and one `filesystem_only_orphan`. The conflicting orphan verifier recorded expected and actual PDF SHA-256 `5027a7331b308945fd4e4062586e893a4f716eb67672de276ea4562ae84dc398`, expected and actual manifest SHA-256 `db8f01647e3667f2f94ee4bda5536a2c80ef31756153a96773349ac480e28fb5`, and byte size 28. It also proved `PilotArtifact` absent, `artifact_exported` audit absent, and payload B absent.

- Canonical pre-rename: post-exit had no binding or final analysis and one partial. Retry returned 200, removed the partial, and left one binding and the exact final analysis file set.
- Canonical post-rename: post-exit final analysis existed without a binding. Retry returned 200 and preserved hashes, sizes, mtimes, and file set.
- Artifact pre-rename: post-exit had no final generation, artifact, or `artifact_exported` audit event and one partial. Retry returned 201, replay returned 201, and the final state has one generation, row, and audit event.
- Artifact post-rename, same bytes: a filesystem generation existed without DB/audit. Retry and replay both returned 201 without changing hashes, sizes, mtimes, DB, audit, or filesystem state.
- Artifact post-rename, conflicting bytes: generation A remained filesystem-only; retry B returned a safe 409 without artifact or export audit. A remained immutable and B was absent from DB, manifest, and all generation files. Classification: `filesystem_only_orphan_conflicting_retry`.

Database, filesystem, and audit snapshots are content-separated. Cleanup recorded Compose down and container/network/volume checks with return code 0, empty resource arrays, and a removed temporary root. SHA256SUMS has 16 valid entries for exactly the 16 required evidence files.

Runtime evidence is local only. Automatic repair is not implemented, ownership is never imported from filesystem, and orphan generations are not deleted. General DB/filesystem reconciliation remains the next stage.
