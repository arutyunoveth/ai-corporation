# Recovery Sprint R2 Technical Spec
## Каноническое восстановление модулей M-031, M-032, M-033, M-034

## 1. Назначение
Recovery Sprint R2 — controlled recovery step для возврата позднего submission/award contour к каноническому master-registry `M-001..M-055`.

В этот шаг входят только канонические модули:
- M-031 Bid Completeness Checker
- M-032 Submission Archive
- M-033 Tender Procedure Monitor
- M-034 Contract Negotiation Workspace

## 2. Цель спринта
К концу Recovery Sprint R2 система должна:
1. иметь канонический M-031 как final completeness and readiness report перед подачей;
2. иметь канонический M-032 как архив поданной версии заявки;
3. иметь канонический M-033 как мониторинг хода процедуры после подачи;
4. иметь канонический M-034 как workspace контрактования после победы;
5. не уничтожить полезную drift-логику submission/control/receipt/outcome;
6. схлопнуть эту логику в helper/internal contours под канонические модули;
7. не создавать новых canonical IDs;
8. сохранить runtime stability.

## 3. Жесткие ограничения
1. Нельзя придумывать новые canonical business modules.
2. Нельзя переписывать старые миграции.
3. Нельзя ломать существующие тесты и endpoints.
4. Нельзя делать destructive rename старых submission modules.
5. Разрешено:
   - вводить canonical alias layer;
   - добавлять новые канонические таблицы и endpoints;
   - использовать current submission/control/receipt/tracker/outcome logic как helper/internal contour;
   - обновлять reconciliation docs и README.

## 4. Recovery strategy
### M-031
Оставить как канонический checker полноты заявки.
Current readiness gate drift-logic не должна жить как отдельный канон, а должна стать helper/internal gating contour вокруг M-031.

### M-032
Вернуть как канонический Submission Archive:
- финальная поданная версия заявки,
- proof of submission,
- archive manifest.

Current submission readiness / control / receipt contours не должны занимать canonical M-032.

### M-033
Вернуть как канонический Tender Procedure Monitor:
- отслеживание статусов процедуры,
- alerts,
- explicit award/loss progression.
Current post-submission tracker / outcome intake логично использовать как helper under M-033.

### M-034
Вернуть как канонический Contract Negotiation Workspace:
- workspace для контрактования после победы,
- negotiation pack,
- tracked comments / negotiation context.

# 5. M-031 — Bid Completeness Checker

## Каноническая роль
Проверяет полноту и согласованность заявки.

## Этап сделки
11

## Статус входа
`BID_READY_FOR_SIGN`

## Входы
- draft bid package
- checklist / required docs list
- collected bid docs
- approval to bid context

## Выходы / артефакты
- final readiness report
- completeness flags
- blocking issues
- readiness summary

## Следующий статус
`BID_READY_FOR_SIGN`

## Сущности
- bid_completeness_sets
- bid_completeness_records
- bid_completeness_flags
- bid_readiness_reports

## API
- POST /bid-completeness/check
- GET /bid-completeness/{bid_completeness_set_id}
- GET /bid-completeness
- GET /bid-completeness/records/{bid_completeness_id}

# 6. M-032 — Submission Archive

## Каноническая роль
Сохраняет финальную поданную версию заявки.

## Этап сделки
12

## Статус входа
`BID_SUBMITTED`

## Входы
- final bid package
- proof of submission
- submission evidence
- final submitted manifest

## Выходы / артефакты
- submission archive
- submission archive items
- proof bundle refs

## Следующий статус
`BID_IN_PROGRESS`

## Сущности
- submission_archive_sets
- submission_archive_records
- submission_archive_items

## API
- POST /submission-archive/build
- GET /submission-archive/{submission_archive_set_id}
- GET /submission-archive
- GET /submission-archive/records/{submission_archive_id}

# 7. M-033 — Tender Procedure Monitor

## Каноническая роль
Отслеживает ход процедуры.

## Этап сделки
13

## Статус входа
`BID_IN_PROGRESS`

## Входы
- tender link
- platform status
- post-submission events
- notices / receipts / outcomes

## Выходы / артефакты
- procedure monitor record
- status updates
- alerts
- procedure event timeline

## Следующий статус
`LOST` / `WON_PENDING_CONTRACT`

## Сущности
- procedure_monitor_sets
- procedure_monitor_records
- procedure_monitor_events
- procedure_monitor_alerts

## API
- POST /procedure-monitor/build
- POST /procedure-monitor/events
- GET /procedure-monitor/{procedure_monitor_set_id}
- GET /procedure-monitor
- GET /procedure-monitor/records/{procedure_monitor_id}

# 8. M-034 — Contract Negotiation Workspace

## Каноническая роль
Готовит контур контрактования.

## Этап сделки
14

## Статус входа
`WON_PENDING_CONTRACT`

## Входы
- final contract
- initial project contract
- supplier plan
- procedure outcome context
- contract review notes

## Выходы / артефакты
- contract negotiation pack
- negotiation workspace record
- negotiation issue list
- tracked comments / clauses

## Следующий статус
`CONTRACT_NEGOTIATION`

## Сущности
- contract_negotiation_sets
- contract_negotiation_records
- contract_negotiation_issues
- contract_negotiation_comments

## API
- POST /contract-negotiation/build
- GET /contract-negotiation/{contract_negotiation_set_id}
- GET /contract-negotiation
- GET /contract-negotiation/records/{contract_negotiation_id}

# 9. Recovery rules for current drift
1. Current submission readiness gate must become helper/internal contour under M-031.
2. Current submission control + receipt registry must become helper/internal contour under M-032.
3. Current post-submission tracker + outcome intake must become helper/internal contour under M-033.
4. Do not expose helper/internal contours as replacement canonical business modules in README/docs.

# 10. Migration order for Recovery Sprint R2
- Migration R2-01: bid completeness report extension
- Migration R2-02: submission archive tables
- Migration R2-03: procedure monitor tables
- Migration R2-04: contract negotiation workspace tables

# 11. Success criteria
1. M-031, M-032, M-033, M-034 are explicitly present as canonical modules.
2. Drift submission helpers are still usable but no longer represented as canonical replacements.
3. README/docs reflect canonical coverage honestly.
4. Existing runtime stays stable.
