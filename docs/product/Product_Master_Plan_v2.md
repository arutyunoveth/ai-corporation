# Product Master Plan v2

## Goal

Turn the recovered tender/procurement skeleton plus the bounded runtime metadata slice into a controlled commercial MVP that can support internal pre-bid analysis and operator-led bid-preparation decisions.

## Sequence

1. Complete bounded runtime metadata Phase `I1`.
2. Ship product docs and public-readiness layer.
3. Add a deterministic commercial pre-bid demo flow.
4. Add controlled LLM-assisted analysis under schema validation and human review.
5. Add an operator-facing commercial skeleton.
6. Add TKP/economics/bid-readiness workflow.
7. Package the repository for a first controlled commercial pilot.

## Operating Boundaries

- `M-049` and `M-050` stay bounded to internal metadata/control and do not authorize broad autonomous runtime.
- `M-052..M-055` remain reconciled late slots and are not promoted to fully implemented runtime modules by this plan.
- All timestamps should remain UTC when new operational artifacts are created.
- All commercial outputs remain reviewable, reproducible, and operator-assisted.

## Success Criteria

- A commercial pre-bid demo can run end-to-end with human-readable output.
- Controlled LLM analysis, if enabled later, remains schema-validated and traceable.
- Operators can review risks, requirements, economics, and next-step recommendations without external execution.
- Product docs remain honest about restrictions and non-goals.
