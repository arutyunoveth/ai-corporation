# R9.3 final-PDF sequential idempotency

Status: `R9_3_ARTIFACT_PUBLICATION_IDEMPOTENCY_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL`

Evidence: `output/r9-artifact-idempotency-20260724T040536Z`

One uvicorn process (PID `28929`) returned health 200 and exited `-15` / `SIGTERM`. Four sequential POST publication attempts each returned 201 and the same artifact `645c950f-68ab-4d81-ab1f-2dbb381e902f` / `1c64e063177e2b2dee9a4f49`.

The immutable PDF SHA-256 was `e8b1bba1c64b6b1703d56ac81ed982e7ae85a77f79c671ed79303de7bf048637`, size `38605`. One PilotArtifact, one PilotRunResult, one `artifact_exported` audit event, and one filesystem generation remained after all replays; PDF/manifest hashes and mtimes were unchanged. Fresh canonical and artifact verifiers passed after every attempt.

The regression test `test_sequential_final_pdf_replays_are_side_effect_free` proves renderer call count one. The acceptance runner records filesystem generation and immutable metadata rather than inventing a runtime renderer counter.

All 38 assertions passed. Hygiene and cleanup passed; SHA256SUMS was generated after the final result. R9.3 does not test concurrent/conflicting publication, interrupted publication, or recovery.
