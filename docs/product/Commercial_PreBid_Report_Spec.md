# Commercial Pre-Bid Report Spec

## Required Sections

1. tender summary
2. why it is relevant
3. technical requirements
4. participant requirements
5. required documents
6. contract risks
7. supplier questions
8. preliminary decision recommendation
9. next actions

## Required Properties

- human-readable Markdown rendering
- structured JSON payload
- deterministic source attribution to persisted deal/intake/document/risk objects
- explicit `analysis_mode`
- explicit human-review posture

## Decision Rules

- the report may produce `GO`, `GO_WITH_CONDITIONS`, or `NEEDS_REVIEW`
- the report is advisory only
- the report must never auto-approve a final bid decision
- the report must never trigger external execution
