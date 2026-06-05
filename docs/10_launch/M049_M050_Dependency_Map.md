# M049 M050 Dependency Map

## Dependency Areas

### Upstream Dependencies

- locked registry `M-001..M-055`
- governance reconciliation documents
- planning constraints from [Deferred_Runtime_Planning_Constraints_Register.md](/Users/master/Documents/AI-Corporation/docs/10_launch/Deferred_Runtime_Planning_Constraints_Register.md)
- current internal/manual-control operational evidence

### M-049 Agent Registry Dependencies

- governance policy for agent lifecycle states
- approval process for future runtime capabilities
- boundary model for what counts as an allowed runtime actor

### M-050 Prompt / Schema Library Dependencies

- governance policy for prompt/schema approval
- versioning and change-control discipline
- traceability expectations for future runtime usage

### Cross-Dependency

- `M-049` depends on knowing what governed runtime artifacts may exist
- `M-050` depends on knowing how governed prompt/schema assets are reviewed and versioned
- both depend on a later explicit runtime design phase, not this planning phase

## Planning Dependency Conclusion

Dependencies are sufficiently known for planning, but not for runtime activation.

## Plan Alignment

- Master Plan matched: yes
- What changed vs plan: dependency relationships were formalized as a repo-local map
- Any drift introduced: `NO`
