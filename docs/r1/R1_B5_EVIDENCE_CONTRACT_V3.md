# B5 evidence contract v3

Each offline run is an acyclic raw-SHA chain: finalized leaf artifacts → `artifacts_manifest.json` → `end_to_end_result.json` → `evidence_validation_result.json` → `bundle_index.json` → detached `bundle_index.sha256`. The manifest includes only leaves and never itself, the result, validation, index, or checksums. The result references only leaves and the manifest; validation references the finalized manifest/result; the index references all three. Release evidence references the two finalized bundle indices and determinism and ends in a detached checksum.

JSON is UTF-8, no BOM, `ensure_ascii=false`, sorted keys, two-space indentation, and one final newline. Every SHA-256 is `sha256(final_file_bytes)` after writing; no file is modified after its digest is referenced. Semantic comparisons normalize only timestamps, run IDs, runtime paths, durations and container/PDF metadata—not procurement facts, rows, evidence, decision, risks or limitations.

Validation rejects non-relative or traversing paths, duplicate logical names/paths, non-leaf manifest entries, missing files, size/hash mismatches, evaluator failures, source-validation failures, security findings, and missing required metrics.
