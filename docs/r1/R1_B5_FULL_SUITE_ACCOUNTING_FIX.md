# Full-suite accounting follow-up

The historical `b5-renderer-fix-run-1-20260714T145000` directory is contaminated legacy evidence. Its archived aggregate recorded 343 executed nodes, while its current mutable shard inventory observes 1552 outcomes; the historical snapshot cannot be reconstructed. It is not used by pytest, resumed, or used as evidence for a new run.

External diagnostic outputs are under `tmp/r1/test-runtime/legacy-verification/b5-renderer-fix-run-1-20260714T145000/`:

- `legacy_evidence_conflict_result.json` records the temporal conflict and arithmetic deficit 1209 without claiming proven missing node IDs.
- `current_runtime_inventory.json` describes current state only.
- `aggregate_compatibility_result.json` and `independent_verification_result.json` fail closed with `missing_frozen_shard_plan`, exit code 2, and `missing_nodeids: null`.

The runner now requires the frozen shard plan for exact accounting, computes terminal nodes from completed shard records, and returns structured `invalid` instead of accepting partial execution. The independent verifier applies the same fail-closed legacy classification without trusting aggregate status. V4 remains blocked until a diagnostic new-format run and two complete exact-suite passes exist.
