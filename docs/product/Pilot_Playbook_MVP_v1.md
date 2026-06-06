# Pilot Playbook MVP v1

## Final Recommendation

`GO with restrictions`

The repository is ready for a first controlled commercial pilot as long as all human-control and no-external-execution restrictions remain in force.

## Pilot Shape

- pilot type: controlled commercial pre-bid pilot
- scope: internal operator-assisted tender analysis and bid-preparation support
- execution mode: manual-control, human-review-required
- external execution: disabled

## Allowed Pilot Activities

- ingest tender materials
- generate deterministic or controlled-LLM pre-bid analysis
- review requirements, risks, and decision recommendations
- prepare manual TKP workspace
- run deterministic economics and bid-readiness checks
- prepare internal `ready_for_human_submission` package

## Forbidden Pilot Activities

- autonomous bid submission
- procurement platform login/upload/submission
- EDS/signature work
- supplier email automation
- uncontrolled external messages
- broad autonomous agent loops

## Recommended Pilot Sequence

1. Run `scripts/run_commercial_mvp_v1_demo.py` in `stub` mode for baseline rehearsal.
2. Confirm the sample flow with the operator console and commercial workspace endpoints.
3. Use one controlled customer-like scenario at a time.
4. Require explicit operator sign-off before any `ready_for_human_submission` state.
5. Keep final submission and all outside communication manual.

## Exit Criteria For The First Paid Pilot

- at least one reproducible demo/customer-like workflow completes end to end
- operator can explain every recommendation and every blocking flag
- no non-goals are violated
- known limitations are accepted explicitly by the pilot stakeholders
