# Dry Run 0 Scenario

## Purpose

`Dry Run 0` is the first controlled end-to-end rehearsal of the recovered company skeleton.

It is designed to validate:

- operator pass-through across the full lifecycle
- control-gate usability
- visibility-helper sufficiency
- audit-trail continuity
- documentation clarity before any real pilot deal is attempted

It is not a real pilot launch.

## Dry Run 0 Scope

- exactly `1` synthetic or максимально приближенный non-production test deal
- internal operator-only execution
- no external platform action
- no real tender submission
- no AI/LLM/agent behavior

## Recommended Input Scenario

Use a deterministic scenario close to the chain already covered in recovery integration tests:

- tender imported and normalized
- screening completed
- supplier path completed
- finance/risk/approval path completed
- bid-prep and procedure-monitor path completed
- contract/execution-entry path completed
- delivery/logistics/incident/acceptance/payment/claim path completed
- closure/postmortem/knowledge path completed

Recommended baseline reference:

- [tests/test_recovery_r5_integration.py](/Users/master/Documents/AI-Corporation/tests/test_recovery_r5_integration.py)

## Expected Flow

### 1. Repo / Governance Gate

Operator confirms:

- source of truth is `main`
- dry-run docs are present
- reserved modules remain reserved
- deferred non-runtime slots remain honestly documented

### 2. Early Procurement Gate

Run / inspect:

- tender import
- tender normalization
- screening
- intake priority
- requirements extraction

Expected result:

- canonical `deal_id` exists
- early qualification artifacts are readable
- control gate after screening is understandable

### 3. Supplier / Commercial Gate

Run / inspect:

- supplier search
- supplier verification
- RFQ / quotes
- quote comparison

Expected result:

- operator can identify the preferred supplier path
- no recommendation is accepted without human review

### 4. Finance / Risk / Approval Gate

Run / inspect:

- cost model
- cash gap
- financing strategy
- finance memo
- contract risks
- integrated risk memo
- CEO approval

Expected result:

- operator can identify assumptions, risks, and explicit approval decision points

### 5. Bid / Procedure Gate

Run / inspect:

- bid documents
- bid package
- bid completeness
- submission archive
- procedure monitor

Expected result:

- operator can verify pre-submit readiness and later procedure state without false automation assumptions

### 6. Contract / Execution Entry Gate

Run / inspect:

- contract negotiation
- supplier contracts
- execution plans
- purchase orders

Expected result:

- obligations and execution assumptions are visible and manually reviewable

### 7. Delivery / Payment / Claims Gate

Run / inspect:

- supplier progress
- logistics tracking
- incident register
- acceptance control
- closing docs
- payment tracking
- claim triggers
- helper `launch_visibility`

Expected result:

- operator can find blocking or risky signals without depending on real-time notifications

### 8. Closure / Learning Gate

Run / inspect:

- deal closure reports
- postmortems
- supplier ratings
- knowledge assets

Expected result:

- the lifecycle can be closed with persisted review artifacts and follow-up knowledge

## Expected Artifacts

At minimum, Dry Run 0 should touch or verify persisted artifacts for:

- deal
- early intake/analysis outputs
- supplier/commercial outputs
- finance/risk/approval outputs
- bid/procedure outputs
- contract/execution-entry outputs
- delivery/payment/claims outputs
- closure/learning outputs
- helper visibility outputs:
  - `/events`
  - `/launch-visibility/build`
  - `/dashboards/build`
  - `/workspace-feed/build`
  - `/action-queue/build`

## Required Control Gates

Dry Run 0 must use the same human-control gates as future `L1`:

- screening review gate
- supplier selection review gate
- finance / risk approval gate
- final bid / sign gate
- procedure outcome review gate
- contract negotiation review gate
- payment / claim review gate

Reference:

- [Launch_L1_Control_Gates.md](/Users/master/Documents/AI-Corporation/docs/10_launch/Launch_L1_Control_Gates.md)

## Required Operator Actions

For each gate, the operator must:

1. identify the persisted artifact set that drives the decision
2. review helper visibility layers if needed
3. record ambiguity, blocker, or friction in the dry-run log
4. avoid any step that would imply autonomous progression

## Expected Outcome

At the end of Dry Run 0, the team should be able to say one of three things:

1. ready to move to Controlled Pilot `L1`
2. ready only after a short blocker-fix step
3. not ready because control/visibility/documentation gaps are still material
