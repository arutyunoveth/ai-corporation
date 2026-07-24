# R9.3 final-PDF sequential idempotency

Status: `R9_3_ARTIFACT_PUBLICATION_IDEMPOTENCY_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL`

Evidence: `output/r9-artifact-idempotency-20260724T053940Z`

One uvicorn process returned health 200 and exited by the expected `SIGTERM`. Four sequential POST publication attempts each returned 201 and the same artifact `f8c76cdc-2361-41e8-b835-7364a067a64b` / `8fad9ac70d37c145240ecec8`.

The immutable PDF SHA-256 was `8147bdd7929dd266cc5f0dc5b5b900bdbf4927a65c19ff387f30e0649b9d58f4`, size `38605`; the real manifest SHA-256 was `27e853eeddba6de8b5f7099661184426dd25f2a6be713e9f6aa50c592392ae71`. Full snapshots after the first publication and after each of the three replays are byte-for-byte equal: one PilotArtifact, one PilotRunResult, one TenderAnalysisRun, and one ProcurementCase. Ordered full audit snapshots contain exactly one `artifact_exported` event and no additional publication events. The generation has exactly one direct child directory named `8fad9ac70d37c145240ecec8`, with exactly `final.pdf` and `artifact.manifest.json`; no partial or renderer-temporary files remain. Fresh canonical and artifact verifiers passed after every attempt.

The regression test `test_sequential_final_pdf_replays_are_side_effect_free` wraps the real PDF renderer and proves a single call across the first publication plus three replays, while comparing PDF and manifest hashes and mtimes after every replay. `test_tampered_existing_artifact_replay_fails_closed` proves a 409 response, no repair, no duplicate artifact, and no additional export audit event for a tampered existing PDF.

All 23 strict assertions passed. The runner's failure-finalization self-test covers a pre-start workflow failure and an injected optional-evidence write failure; both preserve primary failure reporting and return success only when their own validation succeeds. Hygiene, cleanup, and strict SHA256SUMS validation passed. R9.3 does not test concurrent/conflicting publication, interrupted publication, or recovery.
