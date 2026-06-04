# Launch L1 Restrictions

## Purpose

This document defines the non-negotiable operating limits for Launch Sprint `L1`.

`L1` is approved only as a controlled pilot launch.

Dry Run 0 has been completed.

The immediate next operational gate is the explicit Controlled Pilot `L1` go/no-go decision plus closure or conscious acceptance of the agreed minor follow-ups from the dry-run review.

## Allowed Launch Shape

- internal
- pilot-scale
- operator-assisted
- manual-control mode
- explicit human review loops
- documented compensating controls

## Prohibited Launch Claims

`L1` must not be presented as:

- autonomous
- unattended
- self-serve SaaS
- AI-native runtime
- real-time alerting platform
- external execution automation platform

## Canonical Restrictions

The following canonical slots remain intentionally non-open or non-runtime:

- `M-049 Agent Registry` -> `RESERVED`
- `M-050 Prompt / Schema Library` -> `RESERVED`
- `M-052 Notification Layer` -> `PLATFORM_ONLY`
- `M-053 Red Flag Registry` -> `GOVERNANCE_ONLY`
- `M-054 Master Dashboard` -> `PLATFORM_ONLY`
- `M-055 SaaS Productization Tracker` -> `GOVERNANCE_ONLY`

These statuses must not be reframed as fully implemented runtime coverage.

## Runtime Restrictions

At `L1`, the system may be used only with:

- manual event review
- manual dashboard/workspace review
- manual approval and handoff discipline
- human review of risk, incident, payment, and claim signals

The system may not be used with assumptions of:

- automatic notification delivery
- autonomous red-flag escalation
- automated portfolio-level owner oversight
- prompt/agent-based runtime orchestration
- autonomous tender submission or external platform action

## Operator Obligations

Operators must:

1. review persisted artifacts rather than rely on passive alerts
2. verify critical decision points manually
3. record incidents, payment issues, and claims explicitly
4. avoid bypassing canonical audit trails
5. escalate unknown or ambiguous situations to human owners

## Launch Policy Statement

If these restrictions are not acceptable, Launch Sprint `L1` must stop and move into a mini-gap closure step instead of pretending the current runtime is more autonomous than it is.
