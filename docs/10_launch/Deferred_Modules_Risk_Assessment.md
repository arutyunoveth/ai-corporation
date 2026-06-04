# Deferred Modules Risk Assessment

## Purpose

This document explains why the deferred late slots do not automatically block Launch Sprint `L1`, and where their absence still creates risk.

## Risk Matrix

| Canonical ID | Module | Final status | Why deferred / non-runtime | Launch risk if absent | Current compensation | Launch verdict |
|---|---|---|---|---|---|---|
| M-049 | Agent Registry | RESERVED | AI/runtime layer intentionally closed during recovery and reconciliation | No impact on operator-assisted launch because no AI runtime is promised | Human operators, explicit workflow traces, manual decision ownership | Launch allowed without it |
| M-050 | Prompt / Schema Library | RESERVED | Prompt/schema runtime intentionally closed with AI phase deferred | No impact on non-AI launch because prompts are not part of runtime contract | Existing deterministic services and stored schemas/DTOs in code | Launch allowed without it |
| M-052 | Notification Layer | PLATFORM_ONLY | Standalone notification runtime would be artificial before real delivery-channel/product needs are approved | Medium operational visibility risk; critical events may be seen late | Event log, dashboard snapshots, workspace feed, action queue, manual cadence reviews | Launch allowed only with restrictions |
| M-053 | Red Flag Registry | GOVERNANCE_ONLY | Red flags already exist across canonical artifacts; duplicating them into a new silo now would add drift | Medium aggregation risk; operators need discipline to correlate flags | Screening, tech-risk, contract-risk, incident, payment, and claim artifacts plus manual review | Launch allowed only with restrictions |
| M-054 | Master Dashboard | PLATFORM_ONLY | Helper dashboard contours already provide persisted visibility; canonical owner cockpit can wait | Medium owner-visibility risk at larger scale | Dashboard snapshots, workspace feeds, action queues, module-level queries | Launch allowed only with restrictions |
| M-055 | SaaS Productization Tracker | GOVERNANCE_ONLY | Productization is currently a governance/program concern, not a tender-business runtime need | Low direct business-flow risk; medium governance-tracking risk | README, governance docs, launch checklist, manual release discipline | Launch allowed without dedicated runtime |

## Module-By-Module Notes

### M-049 Agent Registry

- Deferred because Launch `L1` is explicitly non-AI.
- No runtime gap exists for a human-operated launch mode.
- Becomes relevant only when role-based AI execution is intentionally opened.

### M-050 Prompt / Schema Library

- Deferred because prompt execution is out of scope.
- Runtime contracts are currently ordinary service/API contracts, not prompt contracts.
- Becomes relevant only when LLM-driven behavior is intentionally introduced.

### M-052 Notification Layer

- This is the most important late-slot operational gap.
- The repo records critical events correctly, but does not proactively notify operators.
- Compensating control must be active review, not passive expectation.

### M-053 Red Flag Registry

- The repo already persists red-flag sources in multiple canonical modules.
- The risk is discoverability and aggregation, not missing data.
- This is acceptable in pilot mode, but weak for scale.

### M-054 Master Dashboard

- Owner visibility exists, but through helper contours and API-driven views rather than a canonical final dashboard.
- Acceptable for internal pilot operations.
- Not acceptable if L1 requires polished portfolio-level executive visibility.

### M-055 SaaS Productization Tracker

- This is mostly a governance/program slot for later productization maturity.
- It does not block the business chain itself.
- The launch package in `docs/10_launch/` acts as the current compensating governance layer.

## Overall Risk Conclusion

- `M-049` and `M-050` are safe to defer for L1.
- `M-055` is also safe to defer for L1.
- `M-052`, `M-053`, and `M-054` are not hard blockers for a controlled pilot, but they are the main reasons launch must be restricted.

## Practical Bottom Line

Launch without these modules is acceptable only if the organization accepts:

- active human supervision
- manual review cadences
- no promise of real-time alerting
- no promise of finished executive cockpit behavior
