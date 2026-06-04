# Recovery Sprint R4 Technical Spec
## Каноническое восстановление модулей M-039, M-040, M-041, M-042, M-043, M-044

## 1. Назначение
Recovery Sprint R4 — controlled recovery step для возврата delivery / acceptance / payment contour к каноническому master-registry `M-001..M-055`.

В этот шаг входят только канонические модули:
- M-039 Logistics Tracker
- M-040 Incident Register
- M-041 Acceptance Control
- M-042 Closing Docs Pack Builder
- M-043 Payment Tracker
- M-044 Claims Trigger Engine

## 2. Цель спринта
К концу Recovery Sprint R4 система должна:
1. иметь канонический M-039 как трекер доставки и ETA;
2. иметь канонический M-040 как реестр отклонений и инцидентов;
3. иметь канонический M-041 как модуль контроля приемки;
4. иметь канонический M-042 как сборщик пакета закрывающих документов;
5. иметь канонический M-043 как трекер оплат и дебиторки;
6. иметь канонический M-044 как триггер претензионного контура;
7. не ломать already-useful helper/internal delivery/payment contours;
8. продолжить controlled recovery без destructive refactor.

## 3. Жесткие ограничения
1. Нельзя создавать новые canonical IDs.
2. Нельзя переписывать старые миграции.
3. Нельзя ломать существующие тесты и endpoints.
4. Нельзя destructive-рефакторить current shipping/acceptance/payment/incident helpers.
5. Разрешено:
   - добавлять canonical tables, services, routers;
   - использовать helper/internal contours как support layer;
   - обновлять reconciliation docs и README.

## 4. Recovery strategy
### M-039
Вернуть как канонический logistics tracking layer:
- shipment tracking dossier,
- ETA,
- delivery checkpoints,
- linked shipment refs.

### M-040
Вернуть как канонический incident register:
- delivery/acceptance/payment incidents,
- issue state,
- incident notes,
- escalation triggers.

### M-041
Вернуть как канонический acceptance control:
- acceptance status,
- remarks,
- acceptance resolution state.

### M-042
Вернуть как канонический closing docs pack builder:
- closing docs pack,
- required closing items,
- closing docs completeness.

### M-043
Вернуть как канонический payment tracker:
- invoice/payment terms,
- collection state,
- overdue tracking,
- payment alerts.

### M-044
Вернуть как канонический claims trigger engine:
- claim trigger flags,
- claim draft context,
- escalation recommendation.

Current helper contours:
- shipping_acceptance
- payment_collection
- incidents/escalations
должны остаться helper/internal layers и не заменять canonical M-039..M-044.

# 5. M-039 — Logistics Tracker

## Каноническая роль
Отслеживает доставку и ETA.

## Этап сделки
17

## Статус входа
`IN_DELIVERY`

## Входы
- shipment data
- milestones
- supplier progress
- purchase order / execution plan context

## Выходы / артефакты
- delivery tracking dossier
- ETA updates
- logistics checkpoints
- linked shipment refs

## Следующий статус
`DELIVERED_PENDING_ACCEPTANCE`

## Сущности
- logistics_tracking_sets
- logistics_tracking_records
- logistics_tracking_events
- logistics_tracking_links

## API
- POST /logistics-tracking/build
- POST /logistics-tracking/events
- GET /logistics-tracking/{logistics_tracking_set_id}
- GET /logistics-tracking
- GET /logistics-tracking/records/{logistics_tracking_id}

# 6. M-040 — Incident Register

## Каноническая роль
Регистрирует отклонения и инциденты.

## Этап сделки
18

## Статус входа
`DELIVERED_PENDING_ACCEPTANCE`

## Входы
- delivery data
- acceptance remarks
- payment alerts
- logistics / supplier progress / acceptance context

## Выходы / артефакты
- incident record
- incident timeline
- incident severity
- escalation flag

## Следующий статус
`ACCEPTED` / incident flow

## Сущности
- incident_register_sets
- incident_register_records
- incident_register_events
- incident_register_flags

## API
- POST /incident-register/build
- POST /incident-register/events
- GET /incident-register/{incident_register_set_id}
- GET /incident-register
- GET /incident-register/records/{incident_register_id}

# 7. M-041 — Acceptance Control

## Каноническая роль
Контролирует приемку и статус замечаний.

## Этап сделки
18

## Статус входа
`DELIVERED_PENDING_ACCEPTANCE`

## Входы
- delivery dossier
- contract terms
- incident context
- acceptance remarks

## Выходы / артефакты
- acceptance status
- acceptance remarks register
- acceptance resolution state
- acceptance dossier

## Следующий статус
`ACCEPTED`

## Сущности
- acceptance_control_sets
- acceptance_control_records
- acceptance_remarks
- acceptance_resolution_items

## API
- POST /acceptance-control/build
- GET /acceptance-control/{acceptance_control_set_id}
- GET /acceptance-control
- GET /acceptance-control/records/{acceptance_control_id}

# 8. M-042 — Closing Docs Pack Builder

## Каноническая роль
Собирает пакет закрывающих.

## Этап сделки
19

## Статус входа
`CLOSING_DOCS_IN_PROGRESS`

## Входы
- acceptance status
- shipment docs
- contract terms
- invoice prerequisites

## Выходы / артефакты
- closing docs pack
- closing docs manifest
- missing closing docs flags

## Следующий статус
`INVOICED`

## Сущности
- closing_docs_sets
- closing_docs_records
- closing_docs_items
- closing_docs_flags

## API
- POST /closing-docs/build
- GET /closing-docs/{closing_docs_set_id}
- GET /closing-docs
- GET /closing-docs/records/{closing_docs_id}

# 9. M-043 — Payment Tracker

## Каноническая роль
Отслеживает дебиторку и сроки оплаты.

## Этап сделки
20

## Статус входа
`INVOICED` / `PAYMENT_PENDING`

## Входы
- invoice data
- payment terms
- closing docs pack
- contract terms

## Выходы / артефакты
- payment tracking log
- overdue alerts
- collection state
- next payment action

## Следующий статус
`PAID`

## Сущности
- payment_tracking_sets
- payment_tracking_records
- payment_tracking_events
- payment_tracking_alerts

## API
- POST /payment-tracking/build
- POST /payment-tracking/events
- GET /payment-tracking/{payment_tracking_set_id}
- GET /payment-tracking
- GET /payment-tracking/records/{payment_tracking_id}

# 10. M-044 — Claims Trigger Engine

## Каноническая роль
Запускает претензионный контур при просрочке.

## Этап сделки
20

## Статус входа
`PAYMENT_PENDING`

## Входы
- payment tracker
- doc status
- overdue events
- incident/payment context

## Выходы / артефакты
- claim draft context
- escalation flag
- claim trigger record

## Следующий статус
`PAYMENT_PENDING` / incident flow

## Сущности
- claim_trigger_sets
- claim_trigger_records
- claim_trigger_flags
- claim_trigger_links

## API
- POST /claim-triggers/build
- GET /claim-triggers/{claim_trigger_set_id}
- GET /claim-triggers
- GET /claim-triggers/records/{claim_trigger_id}

# 11. Recovery rules for current drift
1. Current shipping_acceptance helper must not replace M-039 or M-041.
2. Current incidents helper must not replace canonical M-040.
3. Current payment_collection helper must not replace canonical M-043.
4. Claims logic must surface as explicit canonical M-044 rather than hidden helper logic.
5. Helper contours may stay for runtime continuity, but README/docs must present M-039..M-044 as canonical modules.

# 12. Migration order for Recovery Sprint R4
- Migration R4-01: logistics tracking tables
- Migration R4-02: incident register tables
- Migration R4-03: acceptance control tables
- Migration R4-04: closing docs tables
- Migration R4-05: payment tracking tables
- Migration R4-06: claim trigger tables

# 13. Success criteria
1. M-039..M-044 are explicitly present as canonical modules.
2. Delivery/acceptance/payment contour is represented by canonical business modules, not helper replacements.
3. Existing runtime stays stable.
4. Project is ready for final post-deal recovery step M-045..M-048.
