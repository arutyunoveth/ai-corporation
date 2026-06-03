# Sprint 4A Implementation Summary

## Reused Foundation
- Sprint 1 foundation: `deal`, status model, document store, event log.
- Sprint 2A intake foundation: formal intake package and persisted tender summary.
- Sprint 2B analysis foundation: screening, priority, compliance, requirements, initial tech risks.
- Sprint 3A supplier-side foundation: suppliers, RFQ, communication threads, quotes.
- Sprint 3B supplier quality layer: supplier verification and quote comparison.

## Exact Scope
Sprint 4A adds the economics layer:
- `M-022` Cost Model Engine
- `M-023` Cash Gap Calculator
- `M-024` Financing Strategy Engine
- `M-025` Finance Memo Builder

Resulting formal economics package:
- `cost_model_set + cost_model_record + cost_model_lines`
- `cash_gap_set + cash_gap_record + cash_gap_scenarios`
- `financing_strategy_set + financing_strategy_record + financing_strategy_options`
- `finance_memo_set + finance_memo_record + finance_memo_flags`

## Assumptions / Detected Mismatches
- Sprint 4A source docs were provided outside the repository, so repo-local copies were added under `docs/01_sprints` and `docs/03_entities`.
- Sprint 3B comparison does not yet persist rich contractual payment or delivery terms, so Sprint 4A uses deterministic rule-based economics heuristics derived from formal quote amounts, comparison scores, and persisted financing assumptions.
- `FinanceMemoFlag.severity` reuses the established severity vocabulary `LOW|MEDIUM|HIGH|CRITICAL` instead of introducing a new finance-only enum.
- `FinancingStrategyRecord.feasible` remains a boolean aggregate flag, while individual options keep formal `FEASIBLE|LIMITED|INFEASIBLE` statuses.
- Rebuilds are append-only; there are no separate refresh endpoints in Sprint 4A.

## Planned / Applied Migrations
- `021_create_cost_model`
- `022_create_cash_gap`
- `023_create_financing_strategy`
- `024_create_finance_memo`

## Endpoints Added
- `POST /cost-model/build`
- `GET /cost-model/{cost_model_set_id}`
- `GET /cost-model`
- `GET /cost-model/records/{cost_model_id}`
- `POST /cash-gap/build`
- `GET /cash-gap/{cash_gap_set_id}`
- `GET /cash-gap`
- `GET /cash-gap/records/{cash_gap_id}`
- `POST /financing-strategy/build`
- `GET /financing-strategy/{financing_strategy_set_id}`
- `GET /financing-strategy`
- `GET /financing-strategy/records/{financing_strategy_id}`
- `POST /finance-memo/build`
- `GET /finance-memo/{finance_memo_set_id}`
- `GET /finance-memo`
- `GET /finance-memo/records/{finance_memo_id}`

## Known Limitations
- Economics logic is transparent and rule-based, not a deep financial model.
- Cash-gap scenarios are heuristic and do not yet model real contract schedules.
- Finance memo is a formal persisted object, but not yet integrated with contract-risk parsing or approval workflow.

## Next Step
Sprint 4B can now build on the formal economics package for:
- `M-026` Contract Risk Parser
- `M-027` Integrated Risk Memo Builder
- `M-028` CEO Approval Cockpit
