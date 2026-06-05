# Internal Steady-State Optimization Queue Criteria

## Queue Admission Rules

Only improvements may enter the optimization queue if they:

1. reduce operator friction without changing runtime boundaries
2. improve clarity of manual-control cadence
3. improve use of existing helpers without reframing them as full runtime
4. do not require new canonical IDs
5. do not require AI/runtime reopening

## Queue Rejection Rules

Reject anything that:

- opens deferred/reserved modules
- changes the launch/productization posture
- turns support helpers into new platform runtime
- implies autonomous behavior
