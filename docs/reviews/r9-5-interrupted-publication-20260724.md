# R9.5A interrupted publication boundaries

Status: `R9_5_INTERRUPTED_PUBLICATION_BOUNDARIES_CHARACTERIZED_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL`

Evidence: `output/r9-interrupted-publication-20260724T112948Z`.

The disposable local run took 33.08 seconds. It recorded an 8-point canonical matrix, a 6-point artifact matrix, five hard-kill scenarios, and 68/68 passing assertions. All five faulted processes exited 97; each clean process returned health 200 and exited cleanly. The final hygiene scan passed with `hits: []`; the real hygiene negative self-test and shared-finalization failure self-test both passed.

Six fresh verifier subprocesses passed with exact expected/actual identities: two canonical, three persisted-artifact, and one `filesystem_only_orphan`. The conflicting orphan verifier recorded expected and actual PDF SHA-256 `5027a7331b308945fd4e4062586e893a4f716eb67672de276ea4562ae84dc398`, expected and actual manifest SHA-256 `db8f01647e3667f2f94ee4bda5536a2c80ef31756153a96773349ac480e28fb5`, and byte size 28. It also proved `PilotArtifact` absent, `artifact_exported` audit absent, and payload B absent.

- Canonical pre-rename: post-exit had no binding or final analysis and one partial. Retry returned 200, removed the partial, and left one binding with exactly `requirements.json`, `canonical_report.json`, and `canonical-binding.manifest.json`, with no unexpected entries.
- Canonical post-rename: post-exit and post-retry both had that exact canonical file set. Retry returned 200 and preserved hashes, sizes, and mtimes for every required file.
- Artifact pre-rename: post-exit had no final generation, artifact, or `artifact_exported` audit event and one partial. Retry returned 201, replay returned 201, and the final state has exactly one generation containing only `final.pdf` and `artifact.manifest.json`, one row, and one audit event.
- Artifact post-rename, same bytes: a filesystem generation existed without DB/audit. Retry and replay both returned 201 without changing hashes, sizes, mtimes, DB, audit, or the one exact generation file set.
- Artifact post-rename, conflicting bytes: generation A remained filesystem-only with exactly the required two files; retry B returned a safe 409 without artifact or export audit. A remained immutable and B was absent from DB, manifest, and every generation file. Classification: `filesystem_only_orphan_conflicting_retry`.

Database, filesystem, and audit snapshots are content-separated and include exact canonical and artifact file-set/extra-entry fields. The shared finalization path records actual stage/operation values. Its negative self-test covers a pre-Compose primary failure and an injected optional evidence-write failure: the primary failure is retained, remaining evidence writing and cleanup continue, `evidence_pack_complete` is false, and partial SHA256SUMS validates only files actually written. Cleanup recorded Compose down and container/network/volume checks with return code 0, empty resource arrays, and a removed temporary root. SHA256SUMS has 16 valid entries for exactly the 16 required evidence files.

Runtime evidence is local only. Automatic repair is not implemented, ownership is never imported from filesystem, and orphan generations are not deleted. General DB/filesystem reconciliation remains the next stage.
