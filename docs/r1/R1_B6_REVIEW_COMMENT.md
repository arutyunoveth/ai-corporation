Reviewed `40d6806` against `main` `bc51946`.

Merge rehearsal was conflict-free and the merged-tree focused smoke passed (50 passed). The prior exact-suite acceptance remains valid for the unchanged product code.

Request changes: B5 lacks the required fresh offline E2E artifact set and `end_to_end_result.json` generated from the PR SHA. Please add the reproducible artifact manifest, evaluator outputs, leakage scan and focused-test manifest before owner approval. No production-code defect was found in this review.
