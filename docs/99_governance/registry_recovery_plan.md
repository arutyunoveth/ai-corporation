# Registry Recovery Plan

## Goal

Return the project to the locked canonical business registry `M-001..M-055` without destructive refactors in the current step.

## Progress Snapshot

- Governance lock: completed
- Recovery Sprint R1: completed for `M-005`, `M-007`, `M-008`, `M-010`, `M-012`
- Remaining recovery focus: `M-031`, `M-032`, `M-033`, `M-034`, `M-035..M-055` canonical reconciliation

## Phase 1. Governance Lock And Documentation

1. Lock the canonical module registry in repo docs.
2. Publish canonical-vs-implemented mapping.
3. Publish explicit non-canonical extension register.
4. Rewrite README so drift is no longer presented as official canon.
5. Mark older registry/dependency docs as historical implementation snapshots where needed.

## Phase 2. Naming Cleanup

1. Stop using drift modules as if they were canonical in new docs and future tickets.
2. Introduce wording discipline:
   - `canonical module`
   - `internal helper`
   - `platform service`
   - `adapter`
   - `support contour`
3. Keep current package names temporarily if runtime stability depends on them.

## Phase 3. Alias Layer

1. Define canonical ownership for drift capabilities.
2. Add mapping notes from current package names to canonical destinations.
3. Optionally add doc-level aliases or internal naming comments in code where confusion is highest.
4. Do not rewrite migrations or historical business IDs.

## Phase 4. Controlled Refactor Later

1. Recover missing canonical modules first:
   - `M-005`
   - `M-034`
   - `M-038`
2. Recover partial modules next:
   - `M-007`
   - `M-008`
   - `M-010`
   - `M-031`
3. Then resolve highest-risk mismatches:
   - `M-012`
   - `M-032`
   - `M-033`
   - `M-035..M-037`
   - `M-052..M-055`
4. Only after canonical coverage is stabilized should deeper package/schema refactoring be considered.

## Suggested Recovery Order

### Step 1

Docs cleanup and governance lock.

### Step 2

Recover canonical intake semantics:

- `M-007`
- `M-008`
- `M-010`
- `M-012`

Status: completed in Recovery Sprint R1.

### Step 3

Recover canonical submission semantics:

- `M-032`
- `M-033`
- `M-035`
- `M-036`
- `M-037`

### Step 4

Recover canonical execution / closure semantics:

- `M-038`
- `M-039..M-048`

### Step 5

Recover canonical governance / platform semantics:

- `M-049`
- `M-050`
- `M-052`
- `M-053`
- `M-054`
- `M-055`

## Non-Goals For This Step

- no mass package renames
- no destructive schema rewrite
- no migration history edits
- no endpoint removals
- no runtime behavior changes unless a future reconciliation step explicitly requires them

## Exit Condition

The repository is ready for future work only when every new implementation request is framed against the locked canonical registry first, and any non-canonical capability is deliberately placed into helper/platform/adapter space instead of silently becoming new canon.
