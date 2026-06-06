# MVP Implementation Delivery Sequence

## Delivery Principle

Sequence must preserve the boundary between metadata/control implementation and any later execution-oriented work.

## Proposed Phase 1 Order

1. introduce internal metadata structures for `M-049`
2. introduce internal metadata structures for `M-050`
3. introduce reviewed reference links between the two
4. introduce activation-state handling without live execution
5. add tests that prove bounded scope and non-executing behavior

## Explicit Non-Sequence

This sequence does **not** include:

- agent execution
- prompt execution
- notification runtime activation
- dashboard runtime activation
- productization/runtime packaging

## Delivery Guardrail

If work items start requiring execution behavior, they belong to a later phase and must not be pulled into MVP Phase 1 by default.

## Plan Alignment

- Master Plan matched: `yes`
- What changed vs plan: `delivery order fixed for the narrow slice only`
- Any drift introduced: `no`
