# Limited Runtime Implementation Safety Lock

## Core Safety Lock

1. Do not implement runtime during this phase.
2. Do not open more than one approved MVP slice.
3. Do not present supporting slots as complete runtime.
4. Do not introduce AI-native, autonomous, or self-serve claims.
5. Do not change canonical/governance truth to make scope look larger.

## Allowed First-Step Boundaries

- define one first MVP slice
- document exact in-scope items
- document exact out-of-scope items
- document readiness, rollback, and test expectations
- decide whether the slice may proceed to implementation

## Forbidden Expansions

- broad deferred-slot activation
- implementation by implication
- README wording that sounds like MVP already exists
- hidden conversion of platform/governance slots into runtime-complete modules

## Safety Review Rule

If any artifact starts reading like implementation rather than gate definition, the correct action is `pause` and re-scope.
