# Pilot Outcome Decision Rubric

Use this rubric to determine the final outcome after a design-partner pilot cycle.

## Decision Options

| Decision | Meaning | Next Step |
|----------|---------|-----------|
| `continue_design_partner` | Pilot useful but needs more iteration | Another design-partner cycle |
| `offer_discounted_paid_pilot` | Strong signal, ready for a low-risk paid pilot | Prepare paid pilot offer |
| `not_ready` | Product or workflow not mature enough | Iterate before next pilot |
| `pause` | Partner or team needs a break | Resume when ready |
| `stop` | Use case not viable | Re-evaluate product direction |

## Scoring Guide

### Usefulness Score
- **5**: Partner would use this as-is in real workflow.
- **4**: Partner sees clear value with minor changes.
- **3**: Partner sees potential but needs significant iteration.
- **2**: Partner struggles to find use case.
- **1**: Partner sees no value.

### Clarity Score
- **5**: Crystal clear, no questions.
- **4**: Mostly clear, minor questions.
- **3**: Somewhat clear, needs explanation.
- **2**: Confusing, major rework needed.
- **1**: Incomprehensible.

### Trust Score
- **5**: High trust in accuracy and recommendations.
- **4**: Trust with minor verification needed.
- **3**: Moderate trust, significant verification needed.
- **2**: Low trust, major concerns.
- **1**: No trust in outputs.

## Would-Pay Signal

| Signal | Interpretation |
|--------|----------------|
| `true` | Strong conversion readiness — candidate for paid pilot offer |
| `false` | Not yet ready — need to iterate |
| `None` | Unclear — follow up with partner |

## Conversion Readiness

| Level | Description |
|-------|-------------|
| `high` | Partner expressed willingness to pay. Prepare paid pilot offer. |
| `medium` | Partner sees value but needs polish. One more iteration. |
| `low` | Partner not convinced. Re-evaluate use case fit. |
