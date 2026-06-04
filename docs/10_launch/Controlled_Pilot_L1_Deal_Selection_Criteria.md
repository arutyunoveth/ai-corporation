# Controlled Pilot L1 Deal Selection Criteria

## Allowed Pilot Deals

A deal may be selected for Controlled Pilot L1 only if all of the following are true:

1. canonical `deal_id` exists
2. intake / normalization / screening artifacts already exist
3. supplier/commercial path is readable from persisted artifacts
4. finance/risk/approval path is readable from persisted artifacts
5. bid/procedure path is readable from persisted artifacts
6. execution / delivery / payment / claim supervision is possible with existing manual controls
7. the deal can be run without any external autonomous action claim
8. owner, operator, and reviewer are explicitly assigned

## Preferred Pilot Deals

Prefer deals that are:

- understandable from existing persisted artifacts
- rich enough to exercise major control gates
- low enough risk to tolerate manual supervision
- representative of normal operator workflow

## Disallowed Pilot Deals

Do not select deals that require:

- opening `M-049` / `M-050`
- pretending `M-052..M-055` are fully implemented runtime modules
- real-time notification guarantees
- autonomous submission or external execution claims
- undocumented manual workarounds outside the runbook
- broad rollout or broad launch pressure during the pilot phase

## Deal Count Limit

- minimum planned deal count: `1`
- maximum pilot wave size before S4 review: `2`

## Selection Decision Rule

- Deal #1 should be the cleanest representative deal.
- Deal #2 should be selected to confirm repeatability, not to expand scope.

## Plan Alignment

- Master Plan matched: yes
- What changed vs plan: none beyond formalization into repo-local criteria
- Any drift introduced: `NO`
