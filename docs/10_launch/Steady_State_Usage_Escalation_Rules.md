# Steady-State Usage Escalation Rules

## Escalation Triggers

Escalate when any of the following appears:

- blocker preventing a full controlled cycle
- workload pressure causing skipped review gates
- hidden dependency on reserved/deferred modules
- pressure to make external or autonomous claims

## Escalation Path

1. operator documents the issue
2. reviewer classifies blocker vs non-blocker
3. owner decides continue / pause / stop
4. any real scope change is deferred to separate review, not implemented in-cycle

## Stop Rule

If a cycle cannot stay within internal, operator-assisted, manual-control mode, it must be paused.
