# Limited Runtime Design Safety Rules

## Core Safety Rules

1. Keep all outputs in docs/contracts/design language only.
2. Keep `M-049` and `M-050` in `RESERVED` posture throughout the phase.
3. Keep `M-052..M-055` in reconciled non-runtime posture throughout the phase.
4. Do not imply implementation readiness unless a later explicit gate says so.
5. Do not change canonical/governance truth to make progress appear larger than it is.

## Design Checkpoint Rules

- every sprint must cite the corresponding locked sprint doc
- every sprint must end with `Plan alignment`, `What changed vs plan`, and `Any drift introduced: yes/no`
- every design checkpoint must record owner, reviewer, proceed/pause result, and UTC timestamp

## Blocked Behaviors

- adding runtime endpoints, models, or migrations for deferred slots
- writing README language that sounds like runtime is already open
- turning design contracts into activation claims
- using AI/agent/prompt language that implies live runtime

## Safety Escalation

If a design artifact cannot be written honestly without sounding like implementation, the correct action is `pause`, not scope expansion.
