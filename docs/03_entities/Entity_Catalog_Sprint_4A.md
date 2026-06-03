# Entity Catalog Sprint 4A
## Modules M-022, M-023, M-024, M-025

## Scope
Covers:
- `M-022` Cost Model Engine
- `M-023` Cash Gap Calculator
- `M-024` Financing Strategy Engine
- `M-025` Finance Memo Builder

Depends on:
- `deal`
- `quote_comparison_set`
- `quote_comparison_row`
- `supplier_verification_set`
- `quote_set`
- `event_record`

## Canonical Refs
- `cost_model_set_id => CMS-YYYY-NNNNNN`
- `cost_model_id => CMD-YYYY-NNNNNN`
- `cash_gap_set_id => CGS-YYYY-NNNNNN`
- `cash_gap_id => CG-YYYY-NNNNNN`
- `financing_strategy_set_id => FSS-YYYY-NNNNNN`
- `financing_strategy_id => FS-YYYY-NNNNNN`
- `finance_memo_set_id => FMS-YYYY-NNNNNN`
- `finance_memo_id => FM-YYYY-NNNNNN`

## Invariants
1. Economics outputs always link to `deal_id`.
2. Cash gap cannot be built without a formal cost model.
3. Financing strategy cannot be built without a formal cash gap.
4. Finance memo cannot be built without upstream economics records.
5. New runs are append-only.

## Entities
### cost_model_set
- `cost_model_set_id`
- `deal_id`
- `quote_comparison_set_id`
- `cost_model_status`
- `created_at`
- `updated_at`

### cost_model_record
- `cost_model_id`
- `cost_model_set_id`
- `base_quote_total`
- `logistics_cost`
- `buffer_cost`
- `overhead_cost`
- `total_cost`
- `min_viable_bid`
- `currency_code`
- `created_at`
- `updated_at`

### cost_model_line
- `cost_model_id`
- `line_code`
- `line_type`
- `amount`
- `currency_code`
- `notes`
- `created_at`

### cash_gap_set
- `cash_gap_set_id`
- `deal_id`
- `cost_model_set_id`
- `cash_gap_status`
- `created_at`
- `updated_at`

### cash_gap_record
- `cash_gap_id`
- `cash_gap_set_id`
- `peak_gap_amount`
- `gap_duration_days`
- `currency_code`
- `notes`
- `created_at`
- `updated_at`

### cash_gap_scenario
- `cash_gap_id`
- `scenario_code`
- `scenario_name`
- `peak_gap_amount`
- `gap_duration_days`
- `created_at`

### financing_strategy_set
- `financing_strategy_set_id`
- `deal_id`
- `cash_gap_set_id`
- `strategy_status`
- `created_at`
- `updated_at`

### financing_strategy_record
- `financing_strategy_id`
- `financing_strategy_set_id`
- `recommended_option_code`
- `feasible`
- `notes`
- `created_at`
- `updated_at`

### financing_strategy_option
- `financing_strategy_id`
- `option_code`
- `option_name`
- `funding_amount`
- `funding_cost`
- `currency_code`
- `feasibility_status`
- `created_at`

### finance_memo_set
- `finance_memo_set_id`
- `deal_id`
- `cost_model_set_id`
- `cash_gap_set_id`
- `financing_strategy_set_id`
- `memo_status`
- `created_at`
- `updated_at`

### finance_memo_record
- `finance_memo_id`
- `finance_memo_set_id`
- `summary_text`
- `structured_summary_json`
- `recommendation`
- `created_at`
- `updated_at`

### finance_memo_flag
- `finance_memo_id`
- `flag_code`
- `severity`
- `summary`
- `created_at`

## Enums
### CostModelStatus
- `BUILT`
- `FAILED`
- `STALE`

### CostLineType
- `BASE_QUOTE`
- `LOGISTICS`
- `BUFFER`
- `OVERHEAD`
- `OTHER`

### CashGapStatus
- `BUILT`
- `FAILED`
- `STALE`

### FinancingStrategyStatus
- `BUILT`
- `FAILED`
- `STALE`

### FinancingFeasibilityStatus
- `FEASIBLE`
- `LIMITED`
- `INFEASIBLE`

### FinanceMemoStatus
- `BUILT`
- `FAILED`
- `STALE`

### FinanceRecommendation
- `GO`
- `GO_WITH_CONDITIONS`
- `NO_GO`
- `NEEDS_REVIEW`
