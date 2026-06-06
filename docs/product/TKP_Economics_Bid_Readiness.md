# TKP / Economics / Bid Readiness

## Purpose

`C5` adds an internal-only commercial workspace that links manual TKP collection, deterministic economics, and bid-readiness checks for the Commercial MVP v1 flow.

This layer is orchestration-only:

- it reuses canonical supplier, quote, economics, approval, and readiness modules;
- it does not open autonomous execution;
- it does not send supplier emails automatically;
- it does not submit bids;
- it does not perform EDS/signature work.

## Available Internal Endpoints

- `POST /commercial-workspace/{deal_id}/supplier-request-draft`
- `POST /commercial-workspace/{deal_id}/tkp/register-manual-batch`
- `POST /commercial-workspace/{deal_id}/readiness/build`
- `GET /commercial-workspace/{deal_id}`
- `POST /commercial-workspace/{deal_id}/actions`

## What The Workspace Produces

### Supplier / TKP layer

- supplier request draft text
- supplier clarification question list
- manual supplier registration into the reusable registry
- manual TKP batch registration with formal quote artifacts
- quote comparison recommendation

### Economics layer

- cost model
- cash-gap estimate
- financing strategy
- finance memo

### Bid-readiness layer

- CEO approval package
- bid document collection
- bid package skeleton
- completeness check
- submission-readiness status

## Human Control Boundaries

- Supplier communication records may be persisted for traceability, but outbound delivery remains manual.
- `ready_for_human_submission` means an internal human-reviewed state only.
- Final submission remains outside repository scope.
- LLM output, if used upstream, still requires schema validation and explicit human review.

## Typical Flow

1. Run the commercial pre-bid demo or prepare an equivalent internal deal baseline.
2. Generate a supplier request draft.
3. Register a manual TKP batch with supplier profiles, contacts, and quote values.
4. Build readiness to produce quote comparison, economics, and initial submission-readiness status.
5. Record internal operator actions such as:
   - `tkp_needed`
   - `tkp_received`
   - `economics_reviewed`
   - `ready_for_human_submission`
6. Review the generated workspace report and keep final submission manual.

## Current Limitations

- No automatic outbound supplier email.
- No quote parsing from uploaded supplier files yet; manual quote values are registered directly.
- No procurement platform integration.
- No automatic legal/commercial final decision.
