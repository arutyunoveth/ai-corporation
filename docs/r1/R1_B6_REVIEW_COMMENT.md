Reviewed `40d6806` against `main` `bc51946`.

Merge rehearsal was conflict-free and the merged-tree focused smoke passed (50 passed). The prior exact-suite acceptance remains valid for the unchanged product code.

Two fresh v2 offline runs now provide complete source validation, extraction/analysis/report evaluator results, timing, manifests, leakage scan, focused result and machine determinism. However, the required raw SHA cross-reference between the manifest and `end_to_end_result.json` is cyclic and has no canonicalization rule. The S1 blocker remains open as `B5_E2E_V2_EVIDENCE_CONTRACT_BLOCKED`; no production-code defect was found and no B6 approval is authorized.
