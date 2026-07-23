# R8 independent review — changes required

## Current assessment

`R8_FULL_ACCEPTANCE_REVIEW_CHANGES_REQUIRED`.

The previous 14-file archive and green CI prove only a limited subset of the
required acceptance contract: five filesystem mutations, two DB mutations, and
seven tenant checks in only the B→A direction. Its general `success` flag was
also used to mark unrelated matrices PASS; it is therefore not merge evidence.

## Required before a merge-ready recommendation

- bidirectional endpoint-by-endpoint tenant isolation with leak and no-mutation checks;
- complete real-HTTP publication and idempotency concurrency assertions;
- parameterized filesystem and DB immutable-field matrices;
- genuine recovery/conflict, pre-096 backfill, cleanup and executable R7 checks;
- self-contained evidence metadata and independent verification of the CI artifact.

PR #12 remains Draft. No merge, tag, deployment, or auto-merge was performed.
