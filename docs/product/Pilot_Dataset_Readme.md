# Pilot Dataset Readme

## Location

- `fixtures/pilot_tenders/`

## Format

Each pilot scenario is stored as JSON and follows the same general shape as the existing commercial pre-bid demo fixture:

- tender metadata
- notice text
- technical specification text
- contract draft text
- participant requirements
- required documents
- sample supplier questions
- sample supplier quotes
- expected decision notes
- expected risk categories

## Running A Scenario

Example:

```bash
.venv/bin/python scripts/run_commercial_prebid_demo.py --fixture controlled_pilot_simple_relevant --provider stub --output-dir tmp/pilot_scenarios
```

## Dataset Safety Rules

- synthetic data only
- no external network fetch
- no real procurement platform records
- no real supplier contact automation
