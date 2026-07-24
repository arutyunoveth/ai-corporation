# R9.5A interrupted publication boundaries

Status: `R9_5_INTERRUPTED_PUBLICATION_BOUNDARIES_CHARACTERIZED_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL`.

Fresh local-only runtime evidence: `output/r9-interrupted-publication-20260724T143348Z`.

The disposable Docker runtime completed in 31.10 seconds with 68/68 assertions true. Its result records `emergency_result=false`, `final_status_reached=true`, `primary_failure=null`, `finalization_failures=[]`, and `cleanup_errors=[]`. Hygiene passed with `hits: []`; cleanup completed with Compose down and container/network/volume checks all returning 0, empty resource arrays, and `temporary_root_removed=true`. The evidence pack has the 16 required files, and `SHA256SUMS` validates 16/16 entries with no missing, unexpected, duplicate, or mismatched files.

The runtime still records an 8-point canonical matrix, a 6-point artifact matrix, five hard-kill scenarios, and six successful verifier subprocesses. The faulted workers exited 97; every clean worker reached health 200 and was stopped. Canonical pre-rename recovers a partial on retry, while canonical post-rename preserves the immutable three-file snapshot. Artifact pre-rename recovers on retry; same-byte post-rename retry/replay remains immutable; conflicting bytes are safely rejected with 409 while the filesystem-only orphan remains unchanged.

`python scripts/acceptance/run_r9_interrupted_publication.py --self-test-failure-finalization` now reports the bounded finalization contract through the same `finalize_with_emergency_guard(...)` used by `main()`:

```json
{"cases":{"missing_cleanup_defaults":{"passed":true},"normal_result_write_emergency_fallback":{"passed":true},"optional_evidence_write_failure":{"passed":true},"real_subprocess_cleanup":{"harness_kill_used":false,"passed":true}},"failed_cases":[],"leaked_processes":[],"passed_cases":4,"total_cases":4}
```

- Missing cleanup defaults produces a normal FAILED result without `KeyError`; defaults are populated, the primary failure is retained, and the exit code is nonzero.
- An injected optional `backend-logs.json` write failure leaves the other payloads and `cleanup.json` present, records `write:backend-logs.json`, continues cleanup, and produces valid partial checksums only for files that exist.
- An injected final normal-result rewrite failure reaches the real emergency writer. The atomic emergency result retains the primary failure, has `status=FAILED`, `emergency_result=true`, `final_status_reached=false`, and exit code 2; no emergency temporary sibling remains.
- A real `sys.executable -c "import time; time.sleep(60)"` subprocess is stopped by the shared finalizer. Its lifecycle row has `process_exited=true`, a return code, and a termination method; the harness kill was not used.

Runtime evidence is local only. This change adds no production behavior: it neither imports ownership from filesystem nor deletes orphan generations, performs automatic repair, changes models or migrations, or expands into a general failure-injection matrix.
