# M049 M050 Readiness Architecture

## Scope

This document covers planning-only readiness architecture for:

- `M-049 Agent Registry`
- `M-050 Prompt / Schema Library`

It does **not** authorize runtime implementation.

## Intended Roles

### M-049 Agent Registry

- formal registry of allowed agent/runtime identities
- governance and activation boundary layer for later runtime work
- control surface for capability declaration, approval, and lifecycle state

### M-050 Prompt / Schema Library

- formal registry of approved prompt/schema assets
- versioning and approval discipline for later runtime use
- dependency surface between registry, prompts, schemas, and downstream runtime consumers

## Architectural Positioning

- both modules remain `RESERVED` at this phase
- neither is activated as runtime
- both require a future explicitly opened runtime design/implementation step

## Boundary Conditions

Before any later runtime opening:

1. registry truth must remain locked and consistent
2. operator/governance controls must be defined
3. prompt/schema lifecycle governance must be explicit
4. deferred activation must not bypass existing manual-control posture

## Planning Conclusion

Readiness architecture is documentable now, but runtime activation remains deferred.

## Plan Alignment

- Master Plan matched: yes
- What changed vs plan: readiness architecture was formalized as a repo-local planning artifact
- Any drift introduced: `NO`
