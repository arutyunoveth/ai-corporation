# Controlled Pilot Scenario Pack

## Purpose

The controlled pilot stage uses a fixed internal scenario pack so the team can validate workflow, evidence capture, and customer-facing outputs without using live customer data.

## Scenario Inventory

| Scenario ID | Fixture Name | Type | Primary Use |
| --- | --- | --- | --- |
| `CP-SC-001` | `controlled_pilot_simple_relevant` | simple relevant tender | baseline operator-assisted pilot run |
| `CP-SC-002` | `controlled_pilot_risky_contract` | risky tender | contract-risk and review-gate communication |
| `CP-SC-003` | `controlled_pilot_no_go_review` | no-go tender | explain decline/defer posture without external action |
| `CP-SC-004` | `controlled_pilot_tkp_economics` | TKP/economics tender | exercise TKP, economics, and readiness value |

## Common Dataset Rules

- all scenarios are synthetic
- no live customer data
- no external fetch
- no supplier outreach automation
- all runs stay inside human-control boundaries

## Expected Pilot Value

- scenario-to-scenario evidence of report usefulness
- operator workflow repeatability
- controlled comparison between straightforward and risky cases
- a reusable base for pilot dry-run automation in later CP sprints
