# R0.02 reconciliation report

## Canonical source decision

The canonical integration line is `origin/main` at `8998ddb`, plus R0 commits on `codex/r0-sync-2026-07-11`. The integration worktree is `/Users/master/Documents/AI-Corporation-r0`.

The pre-existing `/Users/master/Documents/AI-Corporation-live` remains preserved rather than overwritten because it contains uncommitted EIS ingestion work. It is not treated as a clean production checkout.

## Checkout map

| Checkout | Branch / HEAD at discovery | Unique work | R0 decision |
|---|---|---|---|
| `AI-Corporation` | `main` / `1fdb853` | Hermes, Tender Research/RAG, Tender Operator changes | recovered to `recovery/local-r0-reconciled` (`4041ac1`) and selectively integrated |
| `AI-Corporation-live` | `feat/eis-production-ingestion-triage` / `71c2fea` | EIS bulk-ingestion changes, data and migrations | preserved in backup; not treated as canonical runtime |
| historical merge/smoke worktrees | multiple | historical commits only | retained and bundled, not merged automatically |
| `AI-Corporation-r0` | `codex/r0-sync-2026-07-11` | R0 work | canonical integration checkout |

All checkout status, diffs, untracked code archives, and Git refs are in `/Users/master/Documents/arvectum-r0-backups/20260711-145008`.

## Recovered work and conflict rule

The local research/Hermes tree compiled and its focused suite passed before integration. During merge, current `origin/main` and the local checkout had incompatible versions of RAG and Tender Operator files. The final choice is the `origin/main` implementation for overlapping public Tender Operator/RAG interfaces, because its call sites require symbols absent from the older local version. Hermes is retained as an explicitly opt-in internal experiment with deterministic fallback. Its minimal settings are integrated and the focused suite passed.

The experimental EIS gateway transport, reseller triage helper, and their tests were **not** integrated: they require a separate gateway settings model and do not demonstrate a stable legal-entity polling flow. Their source remains in recovery commit `4041ac1` and the verified backup.

## EIS boundary

`getDocsIP` remains the read-only documentation contour, using the individual-token configuration already represented by the Tender Operator client. It is distinct from the legal-entity `services-vbs` / machine-readable bus experiment. The latter has no customer-flow feature flag or production claim in the R0 baseline.

## Verification

```text
compileall Hermes + Tender Research + Tender Operator: PASS
focused Hermes/RAG/Tender Operator suite: 156 passed
```

See `EXPERIMENT_INVENTORY.md` for feature classification and the two experiment records for constraints.
