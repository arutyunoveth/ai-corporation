# Карточка модуля M-004 — Журнал событий и решений

## 1. Общая информация

- **ID модуля:** M-004
- **Название:** Журнал событий и решений
- **Приоритет:** P0
- **Спринт:** 1
- **Тип модуля:** Audit Core / Event Log / Decision Trace Layer
- **Статус:** Draft
- **Связанные документы:**
  - M-001 Deal Card Core
  - M-002 Статусная модель сделки
  - M-003 Хранилище документов
  - оргструктура компании
  - сквозной жизненный цикл сделки
  - ТЗ на реализацию компании
  - таблица этапов сделки
  - реестр модулей системы

---

## 2. Назначение модуля

Модуль `M-004` отвечает за единый журнал всех значимых событий, решений, эскалаций и действий в системе.

Если:
- `M-001` отвечает за **что такое сделка**,
- `M-002` отвечает за **в каком статусе сделка**,
- `M-003` отвечает за **какие документы лежат в основе работы**,

то `M-004` отвечает на вопрос:

**"Что именно произошло в системе, кто это инициировал, почему это произошло и на каком основании было принято решение?"**

### Главный принцип
**Ни одно значимое изменение в системе не должно происходить без следа в журнале событий и решений.**

---

## 3. Роль модуля в системе

Журнал событий и решений нужен для 5 целей:

1. **Auditability**  
   Чтобы всегда можно было восстановить цепочку действий.

2. **Traceability**  
   Чтобы понять, на каком артефакте и на каком событии был основан следующий шаг.

3. **Управление разработкой**  
   Чтобы ни один модуль не создавал “скрытые” переходы и действия.

4. **Управление ИИ-агентами**  
   Чтобы фиксировать, какой агент что сделал, какой output вернул и что из этого было принято системой.

5. **Будущая SaaS-упаковка**  
   Чтобы потом можно было превратить внутренний operating system в прозрачный продукт с доказуемой логикой.

---

## 4. Цель модуля

Создать единый event/decision log, который:

1. принимает любые значимые события системы;
2. принимает человеческие решения;
3. принимает события агентов;
4. принимает события документов и статусов;
5. хранит timestamp, инициатора, контекст и основание;
6. позволяет связать событие со сделкой;
7. позволяет связать событие с артефактами;
8. позволяет воспроизвести историю сделки;
9. поддерживает фильтрацию, поиск и группировку по типам событий.

---

## 5. Границы ответственности модуля

### Модуль отвечает за:
- регистрацию события;
- регистрацию решения;
- регистрацию эскалации;
- регистрацию перехода статуса;
- регистрацию действий агентов;
- регистрацию ручных подтверждений;
- регистрацию ошибок и red flags;
- журналирование ссылок на артефакты;
- хранение event timeline по `deal_id`.

### Модуль не отвечает за:
- сам бизнес-переход статуса;
- сам анализ ТЗ;
- саму экономику;
- саму загрузку документа;
- сам выбор поставщика;
- подачу заявки;
- хранение полной сделки как объекта.

Эти действия делают другие модули, а `M-004` фиксирует, что произошло.

---

## 6. Этапы сделки, на которых работает модуль

**Все этапы сделки.**

Журнал должен покрывать:
- создание сделки,
- изменения статусов,
- загрузку и замену документов,
- outputs агентов,
- approvals,
- отклонения,
- инциденты,
- платежи,
- postmortem.

---

## 7. User story

### Бизнес user story
Как владелец компании,  
я хочу иметь полную хронологию действий и решений по каждой сделке,  
чтобы понимать, почему система приняла именно такие шаги, и чтобы можно было быстро разобраться в ошибках, спорных кейсах и истории сделки.

### Техническая user story
Как orchestrator и AI-layer,  
я хочу писать все значимые действия в единый лог,  
чтобы downstream-модули, UI и аудит могли опираться на единую событийную историю.

---

## 8. Входы модуля

### Источники событий
- system core;
- workflow orchestrator;
- Deal Card updates;
- status transitions;
- document operations;
- AI agent outputs;
- human approvals;
- notification layer;
- incident handling;
- finance/payment layer.

### События входа примеры
- `deal_card_created`
- `deal_status_changed`
- `document_registered`
- `document_version_replaced`
- `agent_run_started`
- `agent_run_completed`
- `agent_output_attached`
- `risk_flag_detected`
- `ceo_approval_requested`
- `ceo_approved_bid`
- `ceo_declined_bid`
- `contract_signed`
- `supplier_delay_detected`
- `payment_overdue`
- `postmortem_completed`

### Минимальный payload
```json
{
  "event_type": "deal_status_changed",
  "deal_id": "DL-2026-000001",
  "initiator_type": "SYSTEM|AGENT|HUMAN",
  "initiator_id": "M-002|Risk & Compliance AI|CEO",
  "event_time": "2026-06-02T10:00:00Z",
  "summary": "Status changed from SCREENING to CANDIDATE",
  "artifact_refs": ["screening_memo_001"],
  "metadata": {}
}
```

---

## 9. Выходы модуля

### Основной output
Event Record / Decision Record / Escalation Record.

### Побочные output
- timeline update по сделке;
- возможность построить chronology view;
- возможность триггерить alerting и аналитические слои;
- feed для dashboard и monitoring.

---

## 10. Каноническая модель event record

## 10.1 Верхний уровень

```json
{
  "event_id": "EV-2026-000001",
  "deal_id": "DL-2026-000001",
  "event_type": "deal_status_changed",
  "event_category": "STATUS|DOCUMENT|AGENT|APPROVAL|RISK|INCIDENT|PAYMENT|SYSTEM",
  "event_time": "2026-06-02T10:00:00Z",
  "initiator": {},
  "payload": {},
  "relationships": {},
  "audit": {}
}
```

---

## 10.2 Блок `initiator`

```json
{
  "initiator_type": "SYSTEM|AGENT|HUMAN",
  "initiator_id": "M-002",
  "initiator_name": "Status Engine"
}
```

---

## 10.3 Блок `payload`

```json
{
  "summary": "Status changed from SCREENING to CANDIDATE",
  "details": {},
  "reason": "Screening completed successfully",
  "severity": "INFO|WARNING|CRITICAL",
  "status_before": "SCREENING",
  "status_after": "CANDIDATE",
  "decision_value": null
}
```

---

## 10.4 Блок `relationships`

```json
{
  "artifact_refs": ["screening_memo_001"],
  "document_refs": ["DOC-2026-000010"],
  "related_event_ids": [],
  "related_transition_id": "TR-000001",
  "related_module_id": "M-002"
}
```

---

## 10.5 Блок `audit`

```json
{
  "created_by_module": "M-004",
  "recorded_at": "2026-06-02T10:00:00Z",
  "is_immutable": true
}
```

---

## 11. Каноническая модель decision record

Для человеческих решений и ключевых системных decision points должен быть выделенный логический подтип события.

```json
{
  "event_id": "EV-2026-000050",
  "deal_id": "DL-2026-000001",
  "event_type": "ceo_approved_bid",
  "event_category": "APPROVAL",
  "event_time": "2026-06-02T12:00:00Z",
  "initiator": {
    "initiator_type": "HUMAN",
    "initiator_id": "CEO",
    "initiator_name": "Никита"
  },
  "payload": {
    "summary": "Bid approved",
    "reason": "Acceptable economics and manageable risk",
    "decision_value": "APPROVED_TO_BID",
    "severity": "INFO"
  },
  "relationships": {
    "artifact_refs": ["risk_memo_001", "finance_memo_001", "approval_record_001"],
    "related_module_id": "M-028"
  },
  "audit": {
    "created_by_module": "M-004",
    "recorded_at": "2026-06-02T12:00:00Z",
    "is_immutable": true
  }
}
```

---

## 12. Каноническая модель escalation record

```json
{
  "event_id": "EV-2026-000080",
  "deal_id": "DL-2026-000001",
  "event_type": "manual_review_required",
  "event_category": "RISK",
  "event_time": "2026-06-02T12:30:00Z",
  "initiator": {
    "initiator_type": "AGENT",
    "initiator_id": "Risk & Compliance AI",
    "initiator_name": "Risk & Compliance AI"
  },
  "payload": {
    "summary": "Manual review required due to ambiguity in technical specification",
    "reason": "Potential false positive on equivalence",
    "severity": "CRITICAL"
  },
  "relationships": {
    "artifact_refs": ["compliance_matrix_001", "risk_flag_004"],
    "related_module_id": "M-027"
  },
  "audit": {
    "created_by_module": "M-004",
    "recorded_at": "2026-06-02T12:30:00Z",
    "is_immutable": true
  }
}
```

---

## 13. Категории событий

Базовый справочник `event_category`:

- `STATUS`
- `DOCUMENT`
- `AGENT`
- `APPROVAL`
- `RISK`
- `INCIDENT`
- `PAYMENT`
- `SYSTEM`
- `NOTIFICATION`
- `POSTMORTEM`

---

## 14. Типы событий

Минимальный набор `event_type`:

### System / Deal
- `deal_card_created`
- `deal_updated`
- `deal_archived`

### Status
- `deal_status_changed`
- `status_transition_rejected`
- `rollback_applied`

### Document
- `document_registered`
- `document_version_replaced`
- `document_marked_as_current`
- `document_archived`

### Agent
- `agent_run_started`
- `agent_run_completed`
- `agent_output_attached`
- `agent_run_failed`

### Approval
- `ceo_approval_requested`
- `ceo_approved_bid`
- `ceo_declined_bid`
- `contract_approved`
- `manual_override_applied`

### Risk / Incident
- `risk_flag_detected`
- `manual_review_required`
- `incident_opened`
- `incident_resolved`
- `supplier_delay_detected`

### Payment
- `invoice_issued`
- `payment_pending`
- `payment_received`
- `payment_overdue`

### Postmortem
- `postmortem_created`
- `knowledge_asset_created`

---

## 15. Бизнес-правила

### Правило 1
Каждое значимое действие должно иметь event record.

### Правило 2
Любое человеческое решение должно иметь отдельный decision record.

### Правило 3
Любая эскалация должна иметь escalation record.

### Правило 4
Event log должен быть append-only на логическом уровне.

### Правило 5
Нельзя “тихо” изменить критический объект без записи события.

### Правило 6
Событие должно ссылаться на `deal_id`.

### Правило 7
Если действие основано на артефакте, event должен содержать `artifact_refs`.

### Правило 8
Если событие критично, оно должно иметь severity не ниже `WARNING` или `CRITICAL`.

---

## 16. Связи с другими модулями

### Модуль потребляется:
- M-051 Workflow Orchestrator
- M-052 Notification Layer
- M-054 Master Dashboard
- Chief of Staff AI
- любые UI/monitoring views
- postmortem и аналитические модули

### Модуль получает данные от:
- M-001 Deal Card Core
- M-002 Статусная модель сделки
- M-003 Хранилище документов
- всех agent-модулей
- human approval cockpit
- finance/payment модулей
- incident modules

---

## 17. API / операции модуля

### 17.1 Record Event
Записывает стандартное событие.

### 17.2 Record Decision
Записывает decision event.

### 17.3 Record Escalation
Записывает escalation event.

### 17.4 Get Event Timeline By Deal
Возвращает хронологию событий по сделке.

### 17.5 Filter Events
Фильтрует события по типу, категории, severity, инициатору, времени.

### 17.6 Get Related Events
Возвращает связанные события.

### 17.7 Export Deal Timeline
Экспортирует timeline сделки.

---

## 18. Пример API-операций

## 18.1 Record Event
```json
{
  "operation": "record_event",
  "payload": {
    "event_type": "document_registered",
    "event_category": "DOCUMENT",
    "deal_id": "DL-2026-000001",
    "initiator_type": "SYSTEM",
    "initiator_id": "M-003",
    "event_time": "2026-06-02T10:00:00Z",
    "summary": "Technical specification registered",
    "severity": "INFO",
    "document_refs": ["DOC-2026-000001"],
    "related_module_id": "M-003"
  }
}
```

## 18.2 Record Decision
```json
{
  "operation": "record_decision",
  "payload": {
    "event_type": "ceo_approved_bid",
    "event_category": "APPROVAL",
    "deal_id": "DL-2026-000001",
    "initiator_type": "HUMAN",
    "initiator_id": "CEO",
    "event_time": "2026-06-02T12:00:00Z",
    "summary": "Bid approved",
    "reason": "Margin acceptable, supplier risk manageable",
    "decision_value": "APPROVED_TO_BID",
    "artifact_refs": ["risk_memo_001", "finance_memo_001", "approval_record_001"]
  }
}
```

---

## 19. Workflow-логика модуля

### Сценарий 1. Логирование системного события
1. Другой модуль выполняет действие.
2. После успешного действия вызывает `record_event`.
3. Событие попадает в общий timeline сделки.
4. Timeline становится доступен UI и downstream monitoring.

### Сценарий 2. Логирование статуса
1. M-002 применяет transition.
2. После этого вызывает `record_event`.
3. В лог сохраняется:
   - from_status
   - to_status
   - event
   - инициатор
   - причина
   - связанные артефакты

### Сценарий 3. Логирование агентного действия
1. Агент стартует.
2. Пишется `agent_run_started`.
3. Агент завершает работу.
4. Пишется `agent_run_completed`.
5. Если есть значимый output — пишется `agent_output_attached`.

### Сценарий 4. Логирование решения
1. Человек принимает решение.
2. Создается approval/decision record.
3. Событие связывается с downstream-переходом статуса.
4. UI показывает это решение в timeline сделки.

---

## 20. Red flags и exceptions

### Red flags
- действие совершено без event record;
- human approval есть, а decision record нет;
- статус изменился, а `deal_status_changed` отсутствует;
- событие есть, но нет `deal_id`;
- событие ссылается на несуществующий артефакт;
- конфликт времени событий;
- event_category не соответствует event_type.

### Exceptions
- пакетная запись событий;
- delayed logging из-за внешнего сбоя;
- импорт исторических событий;
- ручная коррекция некорректной записи.

### Как обрабатывать
- не терять raw event;
- писать technical alert;
- маркировать event как `REQUIRES_RECONCILIATION`;
- запускать проверку консистентности timeline.

---

## 21. UI-требования

### В MVP нужен timeline сделки
Показывать:
- дату и время события;
- категорию;
- тип события;
- summary;
- инициатора;
- severity;
- связанные документы/артефакты;
- быстрый переход в источник события.

### Фильтры
- по категории;
- по типу;
- по severity;
- по периоду;
- по инициатору;
- по наличию human decision.

### Дополнительно
- pinned critical events;
- approval timeline;
- incident timeline;
- export history.

---

## 22. Требования к аудиту и неизменяемости

### Требование 1
Event log логически append-only.

### Требование 2
Удаление event record запрещено.

### Требование 3
Исправление возможно только через:
- corrective event;
- reconciliation event;
- administrative override event.

### Требование 4
Все события должны иметь timestamp и инициатора.

### Требование 5
События критичных решений должны быть неизменяемыми после записи.

---

## 23. Требования к данным

### Таблица / сущность `event_log`
Обязательные поля:
- `event_id`
- `deal_id`
- `event_type`
- `event_category`
- `event_time`
- `initiator_type`
- `initiator_id`
- `summary`
- `severity`
- `created_at`

### Таблица / сущность `event_relationships`
- `event_id`
- `artifact_ref`
- `document_ref`
- `related_event_id`
- `related_module_id`

### Таблица / сущность `decision_log`
Можно как подтип `event_log` или отдельную таблицу:
- `event_id`
- `deal_id`
- `decision_value`
- `reason`
- `approved_by`
- `approved_at`

---

## 24. Definition of Done

Модуль считается готовым, если:

1. Система умеет записывать event record.  
2. Система умеет записывать decision record.  
3. Система умеет записывать escalation record.  
4. Любой transition статуса фиксируется в логе.  
5. Любое critical human decision фиксируется в логе.  
6. По `deal_id` можно получить полный timeline.  
7. События можно фильтровать по типу, категории и severity.  
8. Событие нельзя “потерять” без trace.  
9. Event log можно использовать как основу для dashboard и notification layer.  
10. M-004 интегрирован с M-001, M-002 и M-003.

---

## 25. Тест-кейсы

### Позитивные
1. Запись `deal_card_created`
2. Запись `deal_status_changed`
3. Запись `document_registered`
4. Запись `agent_run_started`
5. Запись `agent_run_completed`
6. Запись `ceo_approved_bid`
7. Построение timeline по сделке

### Негативные
8. Попытка записать event без `deal_id`
9. Попытка записать decision без initiator_type = HUMAN
10. Попытка сослаться на несуществующий артефакт
11. Смена статуса без `deal_status_changed`
12. Пустой `event_type`
13. Нарушение append-only логики

---

## 26. ТЗ для Codex / разработчика

### Задача
Реализовать модуль `M-004 Журнал событий и решений` как единый append-only event/decision log системы.

### Нужно сделать
1. Спроектировать event record schema.
2. Спроектировать decision record / escalation record.
3. Реализовать запись событий.
4. Реализовать запись решений.
5. Реализовать связь события с `deal_id`, документами и артефактами.
6. Реализовать timeline по сделке.
7. Реализовать фильтрацию событий.
8. Реализовать immutable / append-only модель записи.
9. Реализовать UI timeline сделки.
10. Реализовать интеграцию с M-001, M-002, M-003.

### Ограничения
- нельзя допускать silent actions без логирования;
- нельзя удалять критические event records;
- нельзя хранить approvals без decision log;
- нельзя строить timeline только из статусов — нужны все классы событий;
- нельзя путать business events и технические ошибки без явной категории.

### Рекомендация по реализации
Подходит схема:
- таблица `event_log`
- таблица `event_relationships`
- таблица `decision_events` как подтип или расширение
- индекс по `deal_id`, `event_time`, `event_category`, `event_type`
- immutable insert-only записи
- corrective events вместо update/delete

При интеграции:
- M-002 пишет status events
- M-003 пишет document events
- AI-модули пишут agent events
- approval cockpit пишет decision events

---

## 27. Следующий модуль после завершения

После завершения `M-004` логически идет:
- **M-049 Agent Registry**

Почему:
после каркаса сделки, state machine, document store и общего event log следующий критичный слой — это формальный реестр ИИ-агентов, без которого дальше невозможно масштабировать role-based architecture и управлять prompt/schema-контрактами системно.
