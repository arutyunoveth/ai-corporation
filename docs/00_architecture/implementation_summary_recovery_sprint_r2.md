# Implementation Summary Recovery Sprint R2

## Reused Foundation

- Recovery governance layer and canonical registry lock from `docs/99_governance/*`
- Existing bid prep contour:
  - `bid_documents`
  - `bid_packages`
  - `bid_completeness`
  - legacy `submission_readiness`
- Existing submission helper contour:
  - `submission_control`
  - `submission_receipts`
  - `post_submission`
  - `outcome_intake`
- Existing contract-risk contour:
  - `contract_risks`

## Implemented Canonical Modules

- `M-031` Bid Completeness Checker
  - extended with persisted `bid_readiness_reports`
- `M-032` Submission Archive
  - implemented as `submission_archive_sets`, `submission_archive_records`, `submission_archive_items`
- `M-033` Tender Procedure Monitor
  - implemented as `procedure_monitor_sets`, `procedure_monitor_records`, `procedure_monitor_events`, `procedure_monitor_alerts`
- `M-034` Contract Negotiation Workspace
  - implemented as `contract_negotiation_sets`, `contract_negotiation_records`, `contract_negotiation_issues`, `contract_negotiation_comments`

## Assumptions / Detected Mismatches

1. Legacy `submission_readiness` remains a useful helper contour, but canonical `M-031` is now the outward completeness owner via `bid_readiness_reports`.
2. Legacy `submission_control`, `submission_receipts`, `post_submission`, and `outcome_intake` remain runtime helpers and are not presented as replacement canon for `M-032`, `M-033`, or `M-034`.
3. The canonical entity catalog fixes `submission_archive_set_id` to `SAS-YYYY-NNNNNN`, which overlaps by prefix with a legacy shipping-acceptance helper ID. This overlap is retained intentionally because refs stay entity-scoped and the source-of-truth catalog forbids inventing a new canonical prefix.
4. `M-034` opens only from explicit persisted `WON` outcome context; no silent inference from helper execution state is used.

## Migrations

- `065_extend_bid_completeness_with_readiness_report`
- `066_create_submission_archive`
- `067_create_procedure_monitor`
- `068_create_contract_negotiation`

## Endpoints

- `POST /bid-completeness/check`
- `GET /bid-completeness/{bid_completeness_set_id}`
- `GET /bid-completeness`
- `GET /bid-completeness/records/{bid_completeness_id}`
- `POST /submission-archive/build`
- `GET /submission-archive/{submission_archive_set_id}`
- `GET /submission-archive`
- `GET /submission-archive/records/{submission_archive_id}`
- `POST /procedure-monitor/build`
- `POST /procedure-monitor/events`
- `GET /procedure-monitor/{procedure_monitor_set_id}`
- `GET /procedure-monitor`
- `GET /procedure-monitor/records/{procedure_monitor_id}`
- `POST /contract-negotiation/build`
- `GET /contract-negotiation/{contract_negotiation_set_id}`
- `GET /contract-negotiation`
- `GET /contract-negotiation/records/{contract_negotiation_id}`

## Tests Added

- bid completeness check and readiness report persistence
- submission archive build and archive item persistence
- procedure monitor build and event/alert persistence
- contract negotiation workspace build and issue/comment persistence
- linkage to canonical deal, submission, and outcome context
- key R2 events written to event log
- append-only rerun behavior for archive and procedure monitor

## Verification

- `pytest tests/test_recovery_r2_integration.py -q` -> `5 passed`
- `pytest -q` -> `147 passed`
- `AI_CORP_DATABASE_URL=sqlite+pysqlite:///./recovery_r2_verify.db alembic upgrade head` -> success

## Governance Result

- Canonical coverage is now exact for `M-031`, `M-032`, `M-033`, and `M-034`.
- Remaining late-stage recovery is concentrated in `M-035..M-055` plus missing `M-038`.
- Legacy helper contours remain available for runtime stability, but are explicitly documented as helper/internal layers rather than canonical business modules.
