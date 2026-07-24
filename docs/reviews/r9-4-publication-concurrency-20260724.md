# R9.4 final-PDF publication concurrency

Status: `R9_4_FINAL_PDF_PUBLICATION_CONCURRENCY_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL`

Final disposable evidence: `output/r9-publication-concurrency-20260724T072811Z`.
The three-process run lasted 15.90 seconds, used Compose project `r9concfe4e6322` and PostgreSQL port `53932`, and started healthy backends A (PID 93896, port 53948), A2 (PID 93910, port 53962), and B (PID 93915, port 53974). All were stopped, and Compose cleanup left no container, network, volume, or temporary root.

The identical-byte HTTP race sent overlapping requests to A and A2. Both returned 201 for one artifact ID/key, candidate SHA-256 `808fd8c26c1eae689b0d1309c4a28aa2a0cdaf66137e1c61ef9234500c1d3d9c`, size 39, with entry and completion markers exactly A/A2. The conflicting-byte race sent overlapping requests to A and B. It returned 409 and 201; candidate hashes were `808fd8c26c1eae689b0d1309c4a28aa2a0cdaf66137e1c61ef9234500c1d3d9c` and `74eae0ff2929976a0860c451f1a722fba168d80916925901f18a3c0a6edee8bd`, both size 39. B won with the latter hash; the safe 409 body exposed no artifact identity or candidate hash.

Each run retained exactly one PilotArtifact, PilotRunResult, and `artifact_exported` audit event. Its sole generation contained only `final.pdf` and `artifact.manifest.json`; DB, manifest, and PDF bindings matched. Sequential replay returned 201 without an additional renderer marker and left post-race DB/audit/filesystem snapshots unchanged.

Fresh verifier subprocesses ran after race and replay for both scenarios (four invocations): each returned exit code 0 with canonical and artifact verification true. The evidence pack contains six snapshots for each DB/audit/filesystem category, 17 required evidence files, a 17-entry valid `SHA256SUMS`, completed hygiene scan, and passing hygiene/failure-finalization self-tests.

The PostgreSQL contract remains intentionally split: R8 tests deterministic identical bytes and requires 2x201; R9.4 tests equal-size distinct SHA-256 bytes and requires `{201, 409}`. The customer-pilot publisher uses fail-closed candidate SHA-256 and byte-size comparison for the first-publication race, while the verified-existing path preserves R9.3 sequential replay semantics.
