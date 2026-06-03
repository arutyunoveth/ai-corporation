# Карточка модуля M-001 — Deal Card Core

## 1. Общая информация

- **ID модуля:** M-001
- **Название:** Deal Card Core
- **Приоритет:** P0
- **Спринт:** 1
- **Тип модуля:** System Core / Data Core
- **Статус:** Draft
- **Связанные документы:**
  - оргструктура компании;
  - сквозной жизненный цикл сделки;
  - ТЗ на реализацию компании;
  - таблица этапов сделки;
  - реестр модулей системы.

---

## 2. Назначение модуля

Deal Card Core — это центральный объект всей системы.

Он нужен для того, чтобы любая сделка существовала в системе как **единый канонический объект**, внутри которого собираются:
- данные о закупке;
- статусы;
- документы;
- аналитика;
- поставщики;
- экономика;
- риски;
- заявка;
- контракт;
- исполнение;
- закрытие;
- пост-анализ.

### Главный принцип
**Все модули, агенты и workflow работают только через Deal Card.**

Никакой критически важной информации о сделке не должно существовать только:
- в чате,
- в почте,
- в голове,
- в отдельной неучтенной таблице,
- в output одного агента без записи в Deal Card.

---

## 3. Роль модуля в системе

Deal Card Core является:
- корневой сущностью всего deal engine;
- главным контейнером бизнес-данных сделки;
- точкой связывания всех артефактов;
- основой для маршрутизации workflow;
- основой для UI/таблицы сделок;
- основой для аудита решений;
- основой для будущего SaaS-продукта.

Если Deal Card спроектирован правильно, можно безопасно разрабатывать остальные ветки независимо.  
Если Deal Card спроектирован плохо, система распадется на несвязанные куски.

---

## 4. Цель модуля

Создать единый объект `DealCard`, который:

1. однозначно идентифицирует сделку;
2. хранит ее текущее состояние;
3. хранит обязательные бизнес-поля;
4. связывает документы, memo, заявки и исполнение;
5. предоставляет единый API / schema-контракт для других модулей;
6. поддерживает полную историю изменений;
7. позволяет любому следующему модулю понять, что происходило со сделкой раньше.

---

## 5. Границы ответственности модуля

### Модуль отвечает за:
- создание сделки;
- генерацию уникального ID сделки;
- хранение основной карточки;
- хранение ключевых полей состояния;
- связь сделки с артефактами и подмодулями;
- связь сделки со статусной моделью;
- отображение текущего snapshot состояния сделки;
- предоставление данных другим модулям.

### Модуль не отвечает за:
- изменение статусов по правилам workflow;
- хранение файлов как бинарного слоя;
- расчет экономики;
- анализ ТЗ;
- supplier sourcing;
- подачу заявки;
- юридическую логику;
- исполнение контракта.

Эти функции реализуются другими модулями, но они обязаны писать результат в Deal Card.

---

## 6. Этапы сделки, на которых работает модуль

**Все этапы сделки.**

### Почему
Deal Card — сквозной контейнер, который живет от:
- `NEW_SIGNAL`
до
- `KNOWLEDGE_CAPTURED`.

---

## 7. User story

### Базовая user story
Как владелец компании,  
я хочу, чтобы любая закупка и любая сделка были представлены одной карточкой,  
чтобы все ИИ-агенты, статусы, документы, memo и решения были привязаны к одному объекту,  
и я в любой момент мог открыть карточку и увидеть полную картину сделки.

### Техническая user story
Как workflow engine,  
я хочу иметь канонический объект сделки,  
чтобы запускать модули и агентов по одной и той же структуре данных,  
а не по разрозненным payload.

---

## 8. Входы модуля

### События входа
- `new_tender_detected`
- `manual_deal_created`
- `import_deal_from_source`

### Обязательные входные данные для создания карточки
- источник сделки;
- внешний идентификатор закупки или запроса;
- ссылка на закупку или источник;
- тип сделки;
- тип закупочного контура;
- дата/время обнаружения;
- краткое наименование;
- заказчик или неизвестный заказчик;
- базовая сумма, если известна.

### Минимальный payload на создание
```json
{
  "source_type": "EIS|ETP|PRIVATE_PORTAL|MANUAL|EMAIL",
  "external_id": "string",
  "source_url": "string",
  "deal_type": "TENDER_SUPPLY|PRIVATE_RFQ|MANUAL_OPPORTUNITY",
  "procurement_model": "223_FZ|PRIVATE_INDUSTRIAL",
  "created_from_event": "new_tender_detected",
  "title": "string",
  "customer_name": "string",
  "budget_amount": 0,
  "currency": "RUB"
}
```

---

## 9. Выходы модуля

### Основной output
Объект `DealCard`.

### Побочные output
- уникальный внутренний `deal_id`;
- запись в журнал создания;
- начальный snapshot карточки;
- готовность карточки к привязке статуса;
- событие `deal_card_created`.

---

## 10. Структура данных Deal Card

Ниже — рекомендуемая базовая структура.  
Она должна быть реализована как каноническая модель данных.

## 10.1 Верхний уровень

```json
{
  "deal_id": "DL-2026-000001",
  "created_at": "2026-06-02T10:00:00Z",
  "updated_at": "2026-06-02T10:00:00Z",
  "version": 1,
  "status": "NEW_SIGNAL",
  "lifecycle_stage": 0,
  "is_archived": false,
  "source": {},
  "core": {},
  "customer": {},
  "procurement": {},
  "documents": {},
  "analysis": {},
  "suppliers": {},
  "economics": {},
  "bid": {},
  "contract": {},
  "execution": {},
  "closing": {},
  "postmortem": {},
  "audit": {}
}
```

---

## 10.2 Блок `source`

```json
{
  "source_type": "EIS",
  "external_id": "string",
  "source_url": "string",
  "detected_at": "datetime",
  "created_from_event": "new_tender_detected",
  "ingestion_run_id": "string"
}
```

---

## 10.3 Блок `core`

```json
{
  "title": "string",
  "deal_type": "TENDER_SUPPLY|PRIVATE_RFQ|MANUAL_OPPORTUNITY",
  "business_model": "SUPPLIER|MIXED",
  "category": "ELECTRICAL_EQUIPMENT",
  "subcategory": "string",
  "region": "string",
  "priority": "LOW|MEDIUM|HIGH|STRATEGIC",
  "owner_role": "Chief of Staff AI",
  "human_owner": "Никита",
  "strategic_flag": false
}
```

---

## 10.4 Блок `customer`

```json
{
  "customer_id": "nullable string",
  "name": "string",
  "inn": "nullable string",
  "segment": "STATE_LINKED|PRIVATE_INDUSTRIAL|OTHER",
  "contact_data": {},
  "notes": "string"
}
```

---

## 10.5 Блок `procurement`

```json
{
  "procurement_model": "223_FZ|PRIVATE_INDUSTRIAL",
  "procedure_type": "string",
  "publication_date": "nullable datetime",
  "deadline_date": "nullable datetime",
  "budget_amount": 0,
  "currency": "RUB",
  "delivery_place": "string",
  "delivery_deadline": "nullable datetime",
  "platform_name": "string",
  "platform_lot_id": "string"
}
```

---

## 10.6 Блок `documents`

```json
{
  "notice_documents": [],
  "technical_spec_documents": [],
  "contract_documents": [],
  "clarification_documents": [],
  "bid_documents": [],
  "closing_documents": [],
  "document_count": 0,
  "last_document_update_at": "nullable datetime"
}
```

Каждый элемент массива должен ссылаться на document record, а не содержать файл внутри себя.

---

## 10.7 Блок `analysis`

```json
{
  "screening_memo_id": null,
  "intake_summary_id": null,
  "requirement_set_id": null,
  "compliance_matrix_id": null,
  "required_docs_list_id": null,
  "initial_risk_flags": [],
  "risk_memo_id": null,
  "analysis_completeness": 0.0
}
```

---

## 10.8 Блок `suppliers`

```json
{
  "supplier_shortlist_ids": [],
  "rfq_batch_id": null,
  "tkp_set_id": null,
  "comparison_table_id": null,
  "selected_supplier_id": null,
  "supplier_decision_note": null
}
```

---

## 10.9 Блок `economics`

```json
{
  "cost_model_id": null,
  "finance_memo_id": null,
  "cash_gap_model_id": null,
  "financing_strategy": null,
  "target_margin_percent": null,
  "expected_margin_amount": null,
  "approved_bid_limit": null
}
```

---

## 10.10 Блок `bid`

```json
{
  "approval_to_bid": {
    "decision": null,
    "decided_by": null,
    "decided_at": null,
    "comment": null
  },
  "bid_package_id": null,
  "readiness_report_id": null,
  "submitted_at": null,
  "submission_proof_id": null,
  "result": null
}
```

---

## 10.11 Блок `contract`

```json
{
  "contract_status": null,
  "project_contract_doc_id": null,
  "final_contract_doc_id": null,
  "contract_review_memo_id": null,
  "supplier_contract_doc_id": null,
  "signed_at": null
}
```

---

## 10.12 Блок `execution`

```json
{
  "execution_plan_id": null,
  "purchase_order_id": null,
  "milestone_ids": [],
  "incident_ids": [],
  "delivery_tracking_id": null,
  "acceptance_status": null
}
```

---

## 10.13 Блок `closing`

```json
{
  "closing_docs_pack_id": null,
  "invoice_id": null,
  "payment_status": null,
  "payment_record_ids": [],
  "claim_ids": []
}
```

---

## 10.14 Блок `postmortem`

```json
{
  "closure_report_id": null,
  "postmortem_id": null,
  "knowledge_asset_ids": [],
  "supplier_rating_updated": false
}
```

---

## 10.15 Блок `audit`

```json
{
  "created_by_module": "M-001",
  "last_updated_by_module": null,
  "change_count": 0,
  "last_changed_at": null,
  "approval_history": [],
  "escalation_history": []
}
```

---

## 11. Обязательные поля

Следующие поля должны быть обязательными на уровне системы:

- `deal_id`
- `created_at`
- `updated_at`
- `version`
- `status`
- `source.source_type`
- `source.external_id` или системная отметка, почему его нет
- `core.title`
- `core.deal_type`
- `procurement.procurement_model`
- `audit.created_by_module`

---

## 12. Бизнес-правила

### Правило 1
Одна сделка = одна Deal Card.

### Правило 2
Любой артефакт должен быть связан с `deal_id`.

### Правило 3
Любой агент, который создает значимый output, обязан:
- либо обновить Deal Card,
- либо создать связанный artifact record и прикрепить ссылку в Deal Card.

### Правило 4
Нельзя менять критические поля без логирования:
- статус,
- selected_supplier_id,
- approved_bid_limit,
- bid approval,
- final contract,
- payment status.

### Правило 5
Deal Card хранит **не только текущее состояние**, но и ссылки на историю.

### Правило 6
Удаление Deal Card запрещено. Допускается только:
- архивирование,
- soft delete по системной политике,
- пометка как дубликат с trace-связью.

---

## 13. Связи с другими модулями

### Модуль потребляется:
- M-002 Статусная модель сделки
- M-003 Хранилище документов
- M-004 Журнал событий и решений
- M-007 Импорт закупок
- M-009 Screening Engine
- M-011 Документ-инжест
- M-016 Supplier Search
- M-022 Cost Model Engine
- M-028 CEO Approval Cockpit
- и всеми последующими модулями

### Модуль зависит от:
- отсутствуют жесткие зависимости на бизнес-уровне;
- технически может зависеть от базового storage/database слоя.

---

## 14. API / операции модуля

### 14.1 Create Deal Card
Создает новую карточку сделки.

### 14.2 Get Deal Card
Возвращает карточку по `deal_id`.

### 14.3 Update Deal Card Snapshot
Обновляет не-критические поля карточки.

### 14.4 Attach Artifact Reference
Прикрепляет ссылку на артефакт.

### 14.5 Archive Deal Card
Архивирует карточку.

### 14.6 List Deal Cards
Возвращает список карточек по фильтрам.

---

## 15. Пример API-операций

## 15.1 Create
```json
{
  "operation": "create_deal_card",
  "payload": {
    "source_type": "EIS",
    "external_id": "223-ABC-001",
    "source_url": "https://example.com/tender/223-ABC-001",
    "deal_type": "TENDER_SUPPLY",
    "procurement_model": "223_FZ",
    "title": "Поставка электротехнического оборудования",
    "customer_name": "ООО Промышленный заказчик",
    "budget_amount": 12500000,
    "currency": "RUB"
  }
}
```

## 15.2 Response
```json
{
  "deal_id": "DL-2026-000001",
  "status": "NEW_SIGNAL",
  "created": true
}
```

---

## 16. Workflow-логика модуля

### Сценарий 1. Автоматическое создание
1. Приходит событие `new_tender_detected`.
2. Модуль проверяет, нет ли уже Deal Card с тем же внешним ID.
3. Если нет — создает новую карточку.
4. Если есть — не создает дубль, а пишет событие `duplicate_detected`.
5. Отдает событие `deal_card_created`.

### Сценарий 2. Ручное создание
1. Пользователь вручную добавляет opportunity.
2. Создается Deal Card с источником `MANUAL`.
3. Дальше сделка идет по тем же правилам, что и автоматическая.

### Сценарий 3. Обновление
1. Следующий модуль создал артефакт.
2. Deal Card получает ссылку на него.
3. Обновляется `updated_at`, `version`, `audit.last_updated_by_module`.

---

## 17. Red flags и exceptions

### Red flags
- попытка создать дубликат сделки;
- отсутствие критического источника или идентификатора;
- попытка обновить карточку без `deal_id`;
- попытка перезаписать критическое поле без аудита;
- попытка удалить карточку физически;
- расхождение внешнего ID и уже существующей сделки.

### Exceptions
- закупка пришла из нескольких источников;
- внешний ID отсутствует у частного RFQ;
- вручную созданная сделка без бюджета;
- дубликат оказался не дубликатом, а связанным лотом.

### Как обрабатывать
- писать в event log;
- не ломать карточку;
- ставить флаг ручной проверки;
- сохранять traceability.

---

## 18. UI-требования

### В MVP нужен экран / представление:
- список сделок;
- фильтр по статусу;
- фильтр по заказчику;
- фильтр по дедлайну;
- индикатор риска;
- индикатор стадии сделки;
- быстрый переход в карточку.

### Внутри Deal Card нужно отображать:
- базовый summary;
- текущий статус;
- ключевые даты;
- customer;
- budget;
- список документов;
- linked memo;
- supplier block;
- finance block;
- bid block;
- execution block;
- audit trail.

---

## 19. Требования к аудиту

При каждом обновлении Deal Card логировать:
- кто изменил;
- какой модуль изменил;
- что изменилось;
- когда изменилось;
- почему изменилось;
- была ли это автоматическая операция или ручная.

### Особо отслеживать:
- approval history;
- status transition references;
- selected supplier changes;
- approved bid limit changes;
- contract reference changes;
- payment status changes.

---

## 20. Требования к версии данных

Deal Card должна поддерживать:
- `version`;
- `updated_at`;
- history of changes;
- возможность восстановить snapshot на определенный момент времени;
- trace между карточкой и историей артефактов.

---

## 21. Definition of Done

Модуль считается готовым, если:

1. Можно создать Deal Card вручную и автоматически.  
2. Каждая карточка получает уникальный `deal_id`.  
3. Карточка хранит обязательные поля.  
4. Карточка поддерживает вложенные блоки данных.  
5. Карточка умеет хранить ссылки на артефакты, а не только raw-текст.  
6. Невозможно создать незалогированный дубль без флага.  
7. Любое изменение карточки попадает в audit trail.  
8. Другие модули могут читать и обновлять карточку через формальный контракт.  
9. Есть список сделок и просмотр одной карточки.  
10. Карточка может быть использована как источник правды для следующего модуля `M-002`.

---

## 22. Тест-кейсы

### Позитивные
1. Создание карточки по событию из ЕИС.
2. Создание карточки вручную.
3. Привязка screening memo к карточке.
4. Обновление supplier блока без потери версии.
5. Отображение карточки в списке.

### Негативные
6. Повторное создание сделки с тем же external_id.
7. Попытка обновления без `deal_id`.
8. Попытка сменить критическое поле без записи в audit.
9. Попытка физического удаления карточки.
10. Попытка создать карточку без обязательного `title`.

---

## 23. ТЗ для Codex / разработчика

### Задача
Реализовать модуль `M-001 Deal Card Core` как центральную сущность системы.

### Нужно сделать
1. Спроектировать data schema Deal Card.
2. Реализовать операции create / read / update / archive / attach artifact reference / list.
3. Реализовать уникальный `deal_id`.
4. Реализовать защиту от дублей.
5. Реализовать audit trail.
6. Реализовать versioning.
7. Реализовать базовый UI списка и карточки.
8. Реализовать контракт, по которому другие модули смогут ссылаться на `deal_id`.

### Ограничения
- нельзя допускать хранения критической информации вне Deal Card;
- нельзя удалять карточки физически;
- нельзя обновлять критические поля без аудита;
- нельзя проектировать схему только под один сценарий закупки.

### Рекомендация по реализации
Подходит PostgreSQL + JSONB для гибких вложенных блоков, либо гибрид:
- реляционные поля для ключевых атрибутов;
- JSONB для модульных подблоков;
- отдельные таблицы для артефактов и audit log.

---

## 24. Следующий модуль после завершения

После завершения `M-001` логически идет:
- **M-002 Статусная модель сделки**

Почему:
пока нет формальной статусной модели, Deal Card будет только контейнером данных, но не станет управляемым workflow-объектом.
