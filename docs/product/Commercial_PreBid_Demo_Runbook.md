# Commercial Pre-Bid Demo Runbook

## Goal

Run a deterministic commercial pre-bid demo without LLM calls, external execution, supplier outreach, or submission behavior.

## Entry Conditions

- database is migrated and application dependencies are installed
- repository is at or after sprint `C2`
- bounded runtime metadata Phase `I1` remains intact

## Run Options

### API

`POST /commercial-prebid-demo/run`

Request body:

```json
{
  "fixture_name": "commercial_mvp_demo"
}
```

### Script

```bash
python scripts/run_commercial_prebid_demo.py --fixture commercial_mvp_demo
```

The script writes:

- `tmp/commercial_prebid_demo/<deal_id>_prebid_report.md`
- `tmp/commercial_prebid_demo/<deal_id>_prebid_report.json`

## Expected Outputs

- persisted intake, artifact, document-set, summary, requirement, and risk objects
- event log entries for demo start and report creation
- customer-readable Markdown report
- structured JSON report for downstream review

## Safety Boundaries

- deterministic only
- no LLM provider calls
- no supplier emails
- no procurement platform actions
- no bid submission
- no autonomous final decision
