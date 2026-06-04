# Registry Recovery Plan

## Goal

Return the project to the locked canonical business registry `M-001..M-055` without destructive refactors.

## Progress Snapshot

- Governance lock: completed
- Recovery Sprint R1: completed for `M-005`, `M-007`, `M-008`, `M-010`, `M-012`
- Recovery Sprint R2: completed for `M-031`, `M-032`, `M-033`, `M-034`
- Recovery Sprint R3: completed for `M-035`, `M-036`, `M-037`, `M-038`
- Recovery Sprint R4: completed for `M-039`, `M-040`, `M-041`, `M-042`, `M-043`, `M-044`
- Recovery Sprint R5: completed for `M-045`, `M-046`, `M-047`, `M-048`
- Remaining deferred canonical slots: `M-049`, `M-050`
- Remaining platform mismatches: `M-052..M-055`

## Recovery Outcome

1. Canonical business-company coverage is exact for `M-001..M-048` and `M-051`.
2. `M-049` and `M-050` are confirmed parts of the original locked registry. They are not missing numbers.
3. `M-049` and `M-050` remain intentionally reserved because Recovery Sprint R5 explicitly forbids AI/LLM/prompt/agent integration.
4. The next unresolved canonical area is later platform/governance reconciliation `M-052..M-055`.

## Suggested Next Step

After Recovery Sprint R5, the repository is ready for a Launch Sprint `L1` review gate:

- confirm that business recovery is accepted
- confirm that reserved AI/runtime slots `M-049`, `M-050` may open
- decide whether `M-052..M-055` are implemented as canonical business modules or formally downgraded to platform support space

## Non-Goals Still Preserved

- no mass package renames
- no destructive schema rewrite
- no migration history edits
- no endpoint removals
- no hidden AI/LLM introduction during recovery
