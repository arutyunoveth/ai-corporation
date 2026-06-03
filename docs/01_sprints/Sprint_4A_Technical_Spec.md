# Sprint 4A Technical Spec
## Modules M-022, M-023, M-024, M-025

## 1. Purpose
Sprint 4A builds the economics layer on top of:
- Sprint 1 foundation
- Sprint 2A intake foundation
- Sprint 2B analysis foundation
- Sprint 3A supplier-side foundation
- Sprint 3B supplier quality layer

Modules:
- `M-022` Cost Model Engine
- `M-023` Cash Gap Calculator
- `M-024` Financing Strategy Engine
- `M-025` Finance Memo Builder

## 2. Sprint Result
By the end of Sprint 4A the system must:
1. build a formal cost model for a deal;
2. calculate cost baseline and minimum viable bid;
3. calculate cash gap and duration;
4. build financing scenarios;
5. build a persisted finance memo;
6. write event and audit trace;
7. prepare foundation for Sprint 4B.

Output:
`cost model + cash gap + financing strategy + finance memo`

## 3. Out Of Scope
- contract risk parsing
- integrated risk memo
- approval cockpit
- bid prep
- submission
- execution

## 4. Dependencies
Uses:
- deal, event log, document store
- analysis package from Sprint 2B
- supplier quality package from Sprint 3B
- quotes, verification, comparison

## 5. Architecture Principles
1. Economics outputs are persisted business objects.
2. Cost model is separate from financing strategy.
3. Cash gap is a first-class persisted calculation.
4. Finance memo must be explainable and traceable.
5. Every business-significant run emits events.

## 6. M-022 Cost Model Engine
Entities:
- `cost_model_sets`
- `cost_model_records`
- `cost_model_lines`

API:
- `POST /cost-model/build`
- `GET /cost-model/{cost_model_set_id}`
- `GET /cost-model?deal_id=...`
- `GET /cost-model/records/{cost_model_id}`

Events:
- `cost_model_build_started`
- `cost_model_built`
- `cost_model_failed`

Acceptance:
1. set built from quote comparison;
2. record persisted;
3. lines persisted;
4. minimum viable bid persisted;
5. event trace written.

## 7. M-023 Cash Gap Calculator
Entities:
- `cash_gap_sets`
- `cash_gap_records`
- `cash_gap_scenarios`

API:
- `POST /cash-gap/build`
- `GET /cash-gap/{cash_gap_set_id}`
- `GET /cash-gap?deal_id=...`
- `GET /cash-gap/records/{cash_gap_id}`

Events:
- `cash_gap_build_started`
- `cash_gap_built`
- `cash_gap_failed`

Acceptance:
1. set built from cost model;
2. peak gap persisted;
3. duration persisted;
4. scenarios persisted;
5. event trace written.

## 8. M-024 Financing Strategy Engine
Entities:
- `financing_strategy_sets`
- `financing_strategy_records`
- `financing_strategy_options`

API:
- `POST /financing-strategy/build`
- `GET /financing-strategy/{financing_strategy_set_id}`
- `GET /financing-strategy?deal_id=...`
- `GET /financing-strategy/records/{financing_strategy_id}`

Events:
- `financing_strategy_build_started`
- `financing_strategy_built`
- `financing_strategy_failed`

Acceptance:
1. strategy built from cash gap;
2. record persisted;
3. options persisted;
4. recommended option persisted;
5. event trace written.

## 9. M-025 Finance Memo Builder
Entities:
- `finance_memo_sets`
- `finance_memo_records`
- `finance_memo_flags`

API:
- `POST /finance-memo/build`
- `GET /finance-memo/{finance_memo_set_id}`
- `GET /finance-memo?deal_id=...`
- `GET /finance-memo/records/{finance_memo_id}`

Events:
- `finance_memo_build_started`
- `finance_memo_built`
- `finance_memo_failed`

Acceptance:
1. memo built from upstream economics objects;
2. memo record persisted;
3. flags persisted;
4. recommendation persisted;
5. event trace written.
