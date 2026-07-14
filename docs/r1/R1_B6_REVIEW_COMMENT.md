Reviewed `40d6806` against `main` `bc51946`.

Merge rehearsal was conflict-free and the merged-tree focused smoke passed (50 passed). The prior exact-suite acceptance remains valid for the unchanged product code.

V3 replaces the rejected cyclic V2 contract with finalized leaves → manifest → result → validation → bundle index → detached checksum. Two fresh V3 bundles and the release index validate successfully. Status is `B5_E2E_V3_PASS_HUMAN_REREVIEW_REQUIRED`; a fresh B6 human review is required and no merge is authorized.
