# Launch L1 Operator Runbook

## Purpose

This runbook explains how to operate a deal through the `L1` pilot in a controlled human-assisted mode.

Use this runbook together with:

- [Launch_L1_Restrictions.md](/Users/master/Documents/AI-Corporation/docs/10_launch/Launch_L1_Restrictions.md)
- [Launch_L1_Control_Gates.md](/Users/master/Documents/AI-Corporation/docs/10_launch/Launch_L1_Control_Gates.md)
- [Launch_L1_Execution_Checklist.md](/Users/master/Documents/AI-Corporation/docs/10_launch/Launch_L1_Execution_Checklist.md)

## Operator Model

The operator is responsible for:

- driving the deal through the canonical runtime
- reviewing persisted outputs at human-control gates
- checking helper support contours when visibility is needed
- preventing silent progression across risky steps

## End-To-End Flow

### 1. Intake And Early Qualification

Primary runtime artifacts:

- `POST /tender-import/runs`
- `POST /tender-normalization/build`
- `POST /screening/run`
- `POST /intake-priority/build`
- `POST /document-ingestion/sets`
- `POST /document-ingestion/sets/{document_set_id}/runs`
- `POST /requirements/extract`

Operator duties:

1. confirm a canonical `deal_id` exists
2. confirm required source payload and normalized records were persisted
3. review screening outcome before moving further
4. review intake priority rationale and requirement extraction summary

Mandatory manual stop:

- after screening
- after requirement extraction if source docs are incomplete or ambiguous

### 2. Supplier And Commercial Evaluation

Primary runtime artifacts:

- `POST /suppliers`
- `POST /supplier-search/build`
- `POST /rfq/batches/build`
- `POST /quotes/register`
- `POST /quote-comparison/build`
- `POST /supplier-verification/build`

Operator duties:

1. confirm shortlist quality and traceability
2. confirm supplier verification outputs are readable
3. review quote comparison recommendation manually
4. do not auto-accept the recommended supplier

Mandatory manual stop:

- before supplier selection

### 3. Finance, Risk, And Approval

Primary runtime artifacts:

- `POST /cost-model/build`
- `POST /cash-gap/build`
- `POST /financing-strategy/build`
- `POST /finance-memo/build`
- `POST /contract-risks/build`
- `POST /integrated-risk-memo/build`
- `POST /ceo-approval/build`
- `POST /ceo-approval/decide`

Operator duties:

1. review financial assumptions
2. review contract risk outputs
3. review integrated risk memo
4. capture explicit human approval decision

Mandatory manual stop:

- before approval decision

### 4. Bid Preparation And Submission

Primary runtime artifacts:

- `POST /bid-documents/collect`
- `POST /bid-packages/build`
- `POST /bid-completeness/check`
- `POST /submission-archive/build`
- helper contours:
  - `POST /submission-readiness/build`
  - `POST /submission-control/build`
  - `POST /submission-control/start`

Operator duties:

1. confirm collected artifacts match the requirement set
2. review completeness and readiness outputs manually
3. do not treat helper readiness as automatic permission to submit

Mandatory manual stop:

- final bid/sign gate before any real submission action

### 5. Procedure Monitoring And Contract Entry

Primary runtime artifacts:

- `POST /procedure-monitor/build`
- `POST /procedure-monitor/events`
- `POST /contract-negotiation/build`
- `POST /supplier-contracts/build`
- `POST /execution-plans/build`
- `POST /purchase-orders/build`

Operator duties:

1. review procedure outcomes explicitly
2. review negotiation issues and supplier contract draft
3. confirm execution plan and purchase order artifacts are complete

Mandatory manual stop:

- after outcome review
- after contract negotiation review

### 6. Execution, Delivery, And Payment

Primary runtime artifacts:

- `POST /delivery-launch/build`
- `POST /delivery-launch/launch`
- `POST /execution/build`
- `POST /supplier-progress/build`
- `POST /logistics-tracking/build`
- `POST /incident-register/build`
- `POST /acceptance-control/build`
- `POST /closing-docs/build`
- `POST /payment-tracking/build`
- `POST /claim-triggers/build`

Operator duties:

1. confirm launch recommendation and execution context
2. review supplier progress and logistics status
3. record incidents, acceptance issues, payment delays, and claim triggers
4. never rely on passive notification behavior

Mandatory manual stop:

- payment / claim review gate

### 7. Closure And Learning

Primary runtime artifacts:

- `POST /deal-closure-reports/build`
- `POST /postmortems/build`
- `POST /supplier-ratings/build`
- `POST /knowledge-assets/build`

Operator duties:

1. ensure closure evidence is complete
2. record postmortem findings and action items
3. confirm supplier rating update is justified
4. persist reusable knowledge asset

## Helper / Internal Contours Allowed In L1

The following helper contours may be used for pilot operations:

- event log query: `GET /events?deal_id=...`
- launch visibility: `POST /launch-visibility/build`
- dashboard snapshots: `POST /dashboards/build`
- workspace feed: `POST /workspace-feed/build`
- action queue: `POST /action-queue/build`, `POST /action-queue/approve`
- operator sessions where useful

These helpers support visibility and control.

They do not change the fact that `L1` remains manual-control mode.

## Incident / Risk / Claim Handling

If a deal raises uncertainty or degradation:

1. review `screening`, `initial-tech-risks`, `contract-risks`, `incident-register`, `payment-tracking`, and `claim-triggers`
2. append missing material events to `/events`
3. stop progression until a human owner confirms next action
4. record the decision trail explicitly

## Things Forbidden In L1

- opening `M-049` or `M-050`
- presenting helper layers as autonomous runtime
- claiming real-time alert delivery
- claiming self-serve or unattended operation
- using external execution as if it were safe autonomous platform behavior
