# Recovery Sprint R3 Technical Spec
## Каноническое восстановление модулей M-035, M-036, M-037, M-038

## 1. Назначение
Recovery Sprint R3 — controlled recovery step для возврата execution-entry contour к каноническому master-registry `M-001..M-055`.

В этот шаг входят только канонические модули:
- M-035 Supplier Back-to-Back Contract Draft
- M-036 Execution Plan Builder
- M-037 Purchase Order Manager
- M-038 Supplier Progress Monitor

## 2. Цель спринта
К концу Recovery Sprint R3 система должна:
1. иметь канонический M-035 как контур обязательств перед поставщиком;
2. иметь канонический M-036 как execution planning / milestone planning artifact;
3. иметь канонический M-037 как PO / supplier order control module;
4. иметь канонический M-038 как supplier progress monitor;
5. не ломать уже существующие helper/internal execution contours;
6. схлопнуть drift execution helpers под canonical execution-entry modules;
7. закрыть последний явный missing-module из текущей reconciliation table.

## 3. Жесткие ограничения
1. Нельзя создавать новые canonical IDs.
2. Нельзя переписывать старые миграции.
3. Нельзя ломать существующие тесты и endpoints.
4. Нельзя destructive-рефакторить delivery/execution drift contours.
5. Разрешено:
   - добавлять canonical tables, services, routers;
   - использовать existing execution helpers как internal support layer;
   - обновлять reconciliation docs и README.

## 4. Recovery strategy
### M-035
Вернуть как канонический drafting layer обязательств перед поставщиком:
- supplier contract draft,
- linked obligations,
- back-to-back alignment with customer contract.

### M-036
Вернуть как канонический execution planning layer:
- execution plan,
- milestones,
- plan assumptions,
- baseline.

### M-037
Вернуть как канонический purchase order manager:
- PO records,
- supplier order state,
- linked order artifacts.

### M-038
Вернуть как канонический supplier progress monitor:
- supplier progress updates,
- readiness / delays,
- progress alerts.

Current execution helpers:
- delivery launch,
- execution command center,
- delivery milestones,
- supplier fulfillment,
должны остаться helper/internal layers и не заменять canonical M-035..M-038.

# 5. M-035 — Supplier Back-to-Back Contract Draft

## Каноническая роль
Формирует договор / заказ поставщику под обязательства перед заказчиком.

## Этап сделки
14

## Статус входа
`CONTRACT_NEGOTIATION`

## Входы
- final customer contract
- supplier decision / comparison outcome
- negotiation workspace
- contract risk notes
- commercial terms

## Выходы / артефакты
- supplier contract draft
- obligation alignment sheet
- supplier contract comments
- linked supplier contract pack

## Следующий статус
`CONTRACT_SIGNED`

## Сущности
- supplier_contract_sets
- supplier_contract_records
- supplier_contract_obligations
- supplier_contract_comments

## API
- POST /supplier-contracts/build
- GET /supplier-contracts/{supplier_contract_set_id}
- GET /supplier-contracts
- GET /supplier-contracts/records/{supplier_contract_id}

# 6. M-036 — Execution Plan Builder

## Каноническая роль
Строит план исполнения и milestones.

## Этап сделки
15

## Статус входа
`CONTRACT_SIGNED`

## Входы
- signed customer contract
- supplier contract draft / signed supplier contract
- delivery assumptions
- commercial terms
- negotiation outcomes

## Выходы / артефакты
- execution plan
- execution milestones
- plan assumptions
- baseline execution dossier

## Следующий статус
`EXECUTION_PLANNING`

## Сущности
- execution_plan_sets
- execution_plan_records
- execution_plan_milestones
- execution_plan_assumptions

## API
- POST /execution-plans/build
- GET /execution-plans/{execution_plan_set_id}
- GET /execution-plans
- GET /execution-plans/records/{execution_plan_id}

# 7. M-037 — Purchase Order Manager

## Каноническая роль
Создает и отслеживает PO поставщику.

## Этап сделки
15

## Статус входа
`EXECUTION_PLANNING`

## Входы
- execution plan
- supplier contract
- supplier profile
- order quantities / scope

## Выходы / артефакты
- purchase order record
- PO status
- linked supplier order refs
- PO attachments

## Следующий статус
`PO_TO_SUPPLIER_SENT`

## Сущности
- purchase_order_sets
- purchase_order_records
- purchase_order_items
- purchase_order_links

## API
- POST /purchase-orders/build
- GET /purchase-orders/{purchase_order_set_id}
- GET /purchase-orders
- GET /purchase-orders/records/{purchase_order_id}

# 8. M-038 — Supplier Progress Monitor

## Каноническая роль
Следит за готовностью у поставщика.

## Этап сделки
16

## Статус входа
`PRODUCTION_OR_PICKING`

## Входы
- PO record
- supplier updates
- milestone plan
- execution progress context

## Выходы / артефакты
- supplier progress log
- supplier readiness state
- delay/risk alerts
- supplier progress timeline

## Следующий статус
`IN_DELIVERY`

## Сущности
- supplier_progress_sets
- supplier_progress_records
- supplier_progress_events
- supplier_progress_alerts

## API
- POST /supplier-progress/build
- POST /supplier-progress/events
- GET /supplier-progress/{supplier_progress_set_id}
- GET /supplier-progress
- GET /supplier-progress/records/{supplier_progress_id}

# 9. Recovery rules for current drift
1. Current delivery launch/execution command helpers must not replace M-036.
2. Current supplier fulfillment helper must not replace M-038.
3. Current milestone helper may support M-036 internally but canonical execution plan must be explicit.
4. Current helper contours may stay alive for runtime stability, but README/docs must present M-035..M-038 as canonical modules.

# 10. Migration order for Recovery Sprint R3
- Migration R3-01: supplier contract draft tables
- Migration R3-02: execution plan tables
- Migration R3-03: purchase order tables
- Migration R3-04: supplier progress monitor tables

# 11. Success criteria
1. M-035, M-036, M-037, M-038 are explicitly present as canonical modules.
2. M-038 is no longer missing in reconciliation docs.
3. Execution-entry contour is represented by canonical business modules, not by helper replacements.
4. Existing runtime stays stable.
