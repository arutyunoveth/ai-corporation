# Limited Runtime Design Constraints Register

## Hard Constraints

1. Do not open `M-049/M-050` in runtime.
2. Do not declare `M-052..M-055` fully implemented runtime modules.
3. Do not add new canonical IDs.
4. Do not create fake runtime endpoints or models for deferred slots.
5. Do not introduce AI-native, autonomous, or self-serve claims.

## Design Constraints

- outputs must remain architecture/governance artifacts
- current registry truth must remain untouched
- supporting-slot language must stay honest about `PLATFORM_ONLY` and `GOVERNANCE_ONLY`
- any implementation-looking artifact must be stopped and reclassified before merge

## Blocked Areas

- runtime behavior for `M-049 Agent Registry`
- runtime behavior for `M-050 Prompt / Schema Library`
- runtime activation for `M-052 Notification Layer`
- runtime activation for `M-053 Red Flag Registry`
- runtime activation for `M-054 Master Dashboard`
- runtime activation for `M-055 SaaS Productization Tracker`

## Review Trigger

If any proposed artifact starts looking like runtime implementation rather than design, it must be paused and treated as a proposal for a later separately approved phase.
