# Карточка модуля M-002 — Статусная модель сделки

## 1. Общая информация

- **ID модуля:** M-002
- **Название:** Статусная модель сделки
- **Приоритет:** P0
- **Спринт:** 1
- **Тип модуля:** Workflow Core / State Engine
- **Статус:** Draft
- **Связанные документы:**
  - M-001 Deal Card Core
  - оргструктура компании
  - сквозной жизненный цикл сделки
  - ТЗ на реализацию компании
  - таблица этапов сделки
  - реестр модулей системы

---

## 2. Назначение модуля

Модуль `M-002` отвечает за формализацию жизненного цикла сделки через систему статусов и допустимых переходов.

Если `M-001 Deal Card Core` отвечает на вопрос **"где живет сделка?"**,  
то `M-002` отвечает на вопрос **"в каком состоянии находится сделка и куда она может перейти дальше?"**

### Главный принцип
**Ни один значимый процесс в системе не должен происходить вне статусной модели.**

Это нужно, чтобы:
- workflow был управляемым;
- разработка не расползалась по разным веткам;
- не было “висящих” состояний;
- каждый модуль знал, какой статус он принимает и какой обязан выдать дальше;
- можно было проверять покрытие жизненного цикла.

---

## 3. Роль модуля в системе

Статусная модель:
- превращает Deal Card в workflow-объект;
- задает канонический state machine сделки;
- определяет допустимые переходы;
- служит опорой для n8n orchestration;
- служит основой для audit trail;
- служит механизмом контроля целостности разработки.

Без этого модуля:
- агенты будут запускаться бессистемно;
- ветки процесса начнут расходиться;
- нельзя будет понять, какой модуль что должен делать дальше;
- будет невозможно построить нормальный event-driven engine.

---

## 4. Цель модуля

Создать формальную state machine сделки, которая:

1. задает полный перечень статусов;
2. задает допустимые переходы между статусами;
3. задает правила входа и выхода из статуса;
4. задает, какие события могут переводить сделку дальше;
5. задает, какие модули могут менять статус;
6. задает обязательное логирование переходов;
7. запрещает невалидные переходы;
8. поддерживает ручной и автоматический переход по правилам.

---

## 5. Границы ответственности модуля

### Модуль отвечает за:
- перечень статусов сделки;
- описание стадий lifecycle;
- описание переходов;
- проверку допустимости перехода;
- выполнение перехода;
- регистрацию причины перехода;
- регистрацию инициатора перехода;
- публикацию события о переходе;
- возможность увидеть историю переходов.

### Модуль не отвечает за:
- хранение самой полной сделки как объекта;
- анализ ТЗ;
- supplier sourcing;
- экономику;
- bid package;
- контрактование;
- исполнение;
- платежи.

Он только управляет состоянием сделки и переходами между состояниями.

---

## 6. Этапы сделки, на которых работает модуль

**Все этапы сделки.**

Статусная модель должна покрывать путь сделки от:
- `NEW_SIGNAL`
до
- `KNOWLEDGE_CAPTURED`.

---

## 7. User story

### Бизнес user story
Как владелец компании,  
я хочу видеть, в каком состоянии находится каждая сделка и что должно произойти дальше,  
чтобы не терять этапы, не забывать ветки и не допускать хаоса в разработке и операционке.

### Техническая user story
Как workflow engine,  
я хочу иметь формальные правила перехода между статусами,  
чтобы запускать агентов и workflow только при валидном состоянии сделки и не допускать неуправляемых сценариев.

---

## 8. Входы модуля

### Основные входы
- `deal_id`
- текущий статус сделки
- событие перехода
- инициатор перехода
- причина перехода
- дополнительные метаданные перехода

### Минимальный payload
```json
{
  "deal_id": "DL-2026-000001",
  "current_status": "NEW_SIGNAL",
  "requested_status": "SCREENING",
  "transition_event": "deal_card_created",
  "initiator_type": "SYSTEM|AGENT|HUMAN",
  "initiator_id": "M-007|Qualification AI|CEO",
  "reason": "New tender normalized and ready for screening"
}
```

---

## 9. Выходы модуля

### Основной output
- обновленный статус сделки;
- запись о переходе статуса.

### Побочные output
- обновление lifecycle stage;
- событие `deal_status_changed`;
- запись в audit trail;
- запуск downstream workflow.

---

## 10. Канонический перечень статусов

## 10.1 Группа A. Входящие
- `NEW_SIGNAL`
- `SCREENING`
- `REJECTED_EARLY`
- `CANDIDATE`

## 10.2 Группа B. Предтендерная аналитика
- `DOCS_ANALYSIS`
- `SUPPLIER_SOURCING`
- `TKP_COLLECTION`
- `ECONOMICS_REVIEW`
- `RISK_REVIEW`

## 10.3 Группа C. Управленческое решение
- `WAITING_CEO_APPROVAL_TO_BID`
- `APPROVED_TO_BID`
- `DECLINED_TO_BID`

## 10.4 Группа D. Подготовка и участие
- `BID_PREPARATION`
- `BID_READY_FOR_SIGN`
- `BID_SUBMITTED`
- `BID_IN_PROGRESS`
- `LOST`
- `WON_PENDING_CONTRACT`

## 10.5 Группа E. Контракт и исполнение
- `CONTRACT_NEGOTIATION`
- `CONTRACT_SIGNED`
- `EXECUTION_PLANNING`
- `PO_TO_SUPPLIER_SENT`
- `PRODUCTION_OR_PICKING`
- `IN_DELIVERY`
- `DELIVERED_PENDING_ACCEPTANCE`
- `ACCEPTED`

## 10.6 Группа F. Финал
- `CLOSING_DOCS_IN_PROGRESS`
- `INVOICED`
- `PAYMENT_PENDING`
- `PAID`
- `CLOSED_SUCCESS`
- `CLOSED_WITH_INCIDENT`

## 10.7 Группа G. Пост-анализ
- `POSTMORTEM`
- `KNOWLEDGE_CAPTURED`

---

## 11. Карта lifecycle stage

Каждому статусу должен соответствовать номер укрупненного этапа.

```json
{
  "NEW_SIGNAL": 0,
  "SCREENING": 1,
  "REJECTED_EARLY": 1,
  "CANDIDATE": 2,
  "DOCS_ANALYSIS": 3,
  "SUPPLIER_SOURCING": 4,
  "TKP_COLLECTION": 5,
  "ECONOMICS_REVIEW": 6,
  "RISK_REVIEW": 6,
  "WAITING_CEO_APPROVAL_TO_BID": 7,
  "APPROVED_TO_BID": 7,
  "DECLINED_TO_BID": 7,
  "BID_PREPARATION": 8,
  "BID_READY_FOR_SIGN": 8,
  "BID_SUBMITTED": 9,
  "BID_IN_PROGRESS": 9,
  "LOST": 9,
  "WON_PENDING_CONTRACT": 9,
  "CONTRACT_NEGOTIATION": 10,
  "CONTRACT_SIGNED": 10,
  "EXECUTION_PLANNING": 11,
  "PO_TO_SUPPLIER_SENT": 11,
  "PRODUCTION_OR_PICKING": 11,
  "IN_DELIVERY": 11,
  "DELIVERED_PENDING_ACCEPTANCE": 11,
  "ACCEPTED": 11,
  "CLOSING_DOCS_IN_PROGRESS": 12,
  "INVOICED": 12,
  "PAYMENT_PENDING": 12,
  "PAID": 12,
  "CLOSED_SUCCESS": 12,
  "CLOSED_WITH_INCIDENT": 12,
  "POSTMORTEM": 13,
  "KNOWLEDGE_CAPTURED": 13
}
```

---

## 12. Допустимые переходы статусов

Ниже — базовый набор допустимых переходов.

```json
{
  "NEW_SIGNAL": ["SCREENING"],
  "SCREENING": ["REJECTED_EARLY", "CANDIDATE"],
  "REJECTED_EARLY": [],
  "CANDIDATE": ["DOCS_ANALYSIS"],
  "DOCS_ANALYSIS": ["SUPPLIER_SOURCING", "REJECTED_EARLY"],
  "SUPPLIER_SOURCING": ["TKP_COLLECTION", "REJECTED_EARLY"],
  "TKP_COLLECTION": ["ECONOMICS_REVIEW", "REJECTED_EARLY"],
  "ECONOMICS_REVIEW": ["RISK_REVIEW", "REJECTED_EARLY"],
  "RISK_REVIEW": ["WAITING_CEO_APPROVAL_TO_BID", "REJECTED_EARLY"],
  "WAITING_CEO_APPROVAL_TO_BID": ["APPROVED_TO_BID", "DECLINED_TO_BID", "DOCS_ANALYSIS", "SUPPLIER_SOURCING", "ECONOMICS_REVIEW"],
  "APPROVED_TO_BID": ["BID_PREPARATION"],
  "DECLINED_TO_BID": [],
  "BID_PREPARATION": ["BID_READY_FOR_SIGN", "DOCS_ANALYSIS"],
  "BID_READY_FOR_SIGN": ["BID_SUBMITTED", "BID_PREPARATION"],
  "BID_SUBMITTED": ["BID_IN_PROGRESS"],
  "BID_IN_PROGRESS": ["LOST", "WON_PENDING_CONTRACT"],
  "LOST": ["POSTMORTEM"],
  "WON_PENDING_CONTRACT": ["CONTRACT_NEGOTIATION"],
  "CONTRACT_NEGOTIATION": ["CONTRACT_SIGNED", "CLOSED_WITH_INCIDENT"],
  "CONTRACT_SIGNED": ["EXECUTION_PLANNING"],
  "EXECUTION_PLANNING": ["PO_TO_SUPPLIER_SENT"],
  "PO_TO_SUPPLIER_SENT": ["PRODUCTION_OR_PICKING", "CLOSED_WITH_INCIDENT"],
  "PRODUCTION_OR_PICKING": ["IN_DELIVERY", "CLOSED_WITH_INCIDENT"],
  "IN_DELIVERY": ["DELIVERED_PENDING_ACCEPTANCE", "CLOSED_WITH_INCIDENT"],
  "DELIVERED_PENDING_ACCEPTANCE": ["ACCEPTED", "CLOSED_WITH_INCIDENT"],
  "ACCEPTED": ["CLOSING_DOCS_IN_PROGRESS"],
  "CLOSING_DOCS_IN_PROGRESS": ["INVOICED", "CLOSED_WITH_INCIDENT"],
  "INVOICED": ["PAYMENT_PENDING"],
  "PAYMENT_PENDING": ["PAID", "CLOSED_WITH_INCIDENT"],
  "PAID": ["CLOSED_SUCCESS"],
  "CLOSED_SUCCESS": ["POSTMORTEM"],
  "CLOSED_WITH_INCIDENT": ["POSTMORTEM"],
  "POSTMORTEM": ["KNOWLEDGE_CAPTURED"],
  "KNOWLEDGE_CAPTURED": []
}
```

---

## 13. Классы переходов

### 13.1 Автоматические переходы
Переход может делать система или агент без твоего approval:
- `NEW_SIGNAL` → `SCREENING`
- `SCREENING` → `CANDIDATE`
- `CANDIDATE` → `DOCS_ANALYSIS`
- `DOCS_ANALYSIS` → `SUPPLIER_SOURCING`
- `SUPPLIER_SOURCING` → `TKP_COLLECTION`
- `TKP_COLLECTION` → `ECONOMICS_REVIEW`
- `ECONOMICS_REVIEW` → `RISK_REVIEW`
- `APPROVED_TO_BID` → `BID_PREPARATION`
- `BID_SUBMITTED` → `BID_IN_PROGRESS`
- `WON_PENDING_CONTRACT` → `CONTRACT_NEGOTIATION`
- `CONTRACT_SIGNED` → `EXECUTION_PLANNING`
- `ACCEPTED` → `CLOSING_DOCS_IN_PROGRESS`
- `INVOICED` → `PAYMENT_PENDING`
- `PAID` → `CLOSED_SUCCESS`
- `POSTMORTEM` → `KNOWLEDGE_CAPTURED`

### 13.2 Переходы с обязательным human approval
- `WAITING_CEO_APPROVAL_TO_BID` → `APPROVED_TO_BID`
- `WAITING_CEO_APPROVAL_TO_BID` → `DECLINED_TO_BID`
- `BID_READY_FOR_SIGN` → `BID_SUBMITTED`
- `CONTRACT_NEGOTIATION` → `CONTRACT_SIGNED`
- спорные возвраты в предыдущие статусы
- перевод в `CLOSED_WITH_INCIDENT`, если решение носит управленческий характер

### 13.3 Переходы с возвратом назад
Система должна поддерживать controlled rollback:
- `WAITING_CEO_APPROVAL_TO_BID` → `DOCS_ANALYSIS`
- `WAITING_CEO_APPROVAL_TO_BID` → `SUPPLIER_SOURCING`
- `WAITING_CEO_APPROVAL_TO_BID` → `ECONOMICS_REVIEW`
- `BID_PREPARATION` → `DOCS_ANALYSIS`
- `BID_READY_FOR_SIGN` → `BID_PREPARATION`

Rollback должен требовать указания причины.

---

## 14. Бизнес-правила переходов

### Правило 1
У сделки всегда должен быть один и только один текущий статус.

### Правило 2
Нельзя перейти в статус, который не входит в список допустимых переходов.

### Правило 3
Нельзя “перепрыгивать” через обязательные статусы без явного административного исключения.

### Правило 4
Любой переход должен иметь:
- инициатора;
- событие;
- timestamp;
- причину;
- ссылку на артефакт или контекст, если переход бизнес-значим.

### Правило 5
Статус — это не просто label, а управляющий флаг для запуска следующих модулей.

### Правило 6
Финальные статусы без дальнейших переходов:
- `REJECTED_EARLY`
- `DECLINED_TO_BID`
- `KNOWLEDGE_CAPTURED`

### Правило 7
Статусы `LOST`, `CLOSED_SUCCESS`, `CLOSED_WITH_INCIDENT` — не совсем terminal: после них обязателен `POSTMORTEM`.

---

## 15. Связь статуса с артефактами

Каждый критический переход должен быть поддержан артефактом.

### Примеры
- `SCREENING` → `CANDIDATE` требует `screening_memo_id`
- `DOCS_ANALYSIS` → `SUPPLIER_SOURCING` требует `compliance_matrix_id`
- `TKP_COLLECTION` → `ECONOMICS_REVIEW` требует `tkp_set_id`
- `RISK_REVIEW` → `WAITING_CEO_APPROVAL_TO_BID` требует `risk_memo_id`
- `WAITING_CEO_APPROVAL_TO_BID` → `APPROVED_TO_BID` требует approval record
- `BID_PREPARATION` → `BID_READY_FOR_SIGN` требует `bid_package_id`
- `BID_READY_FOR_SIGN` → `BID_SUBMITTED` требует readiness report + человеческое подтверждение
- `CONTRACT_NEGOTIATION` → `CONTRACT_SIGNED` требует final contract reference
- `ACCEPTED` → `CLOSING_DOCS_IN_PROGRESS` требует acceptance evidence
- `PAID` → `CLOSED_SUCCESS` требует payment record
- `POSTMORTEM` → `KNOWLEDGE_CAPTURED` требует postmortem record

---

## 16. API / операции модуля

### 16.1 Validate Transition
Проверяет, можно ли перейти из текущего статуса в requested status.

### 16.2 Apply Transition
Применяет переход и обновляет Deal Card.

### 16.3 Get Current Status
Возвращает текущий статус сделки.

### 16.4 Get Allowed Next Statuses
Возвращает список допустимых следующих статусов.

### 16.5 Get Transition History
Возвращает историю переходов.

### 16.6 Rollback Transition
Выполняет разрешенный возврат в предыдущий статус с указанием причины.

---

## 17. Пример API-операций

## 17.1 Validate
```json
{
  "operation": "validate_transition",
  "payload": {
    "deal_id": "DL-2026-000001",
    "current_status": "TKP_COLLECTION",
    "requested_status": "ECONOMICS_REVIEW",
    "transition_event": "tkp_collection_completed"
  }
}
```

## 17.2 Apply
```json
{
  "operation": "apply_transition",
  "payload": {
    "deal_id": "DL-2026-000001",
    "current_status": "WAITING_CEO_APPROVAL_TO_BID",
    "requested_status": "APPROVED_TO_BID",
    "transition_event": "ceo_approved_bid",
    "initiator_type": "HUMAN",
    "initiator_id": "CEO",
    "reason": "Approved after reviewing finance and risk memo",
    "artifact_refs": ["risk_memo_001", "finance_memo_001", "approval_record_001"]
  }
}
```

---

## 18. Workflow-логика модуля

### Сценарий 1. Линейный автоматический переход
1. Текущий модуль завершает работу.
2. Создает required artifact.
3. Вызывает `validate_transition`.
4. Если переход разрешен — вызывает `apply_transition`.
5. Публикуется `deal_status_changed`.
6. Orchestrator запускает следующий workflow.

### Сценарий 2. Human approval transition
1. Сделка приходит в `WAITING_CEO_APPROVAL_TO_BID`.
2. Cockpit показывает тебе материалы.
3. Ты принимаешь решение.
4. Система записывает approval record.
5. Вызывается `apply_transition`.
6. Следующий workflow запускается только после успешного перехода.

### Сценарий 3. Rollback
1. Выявлен пробел в предыдущем этапе.
2. Система или человек инициирует возврат.
3. Указывается причина rollback.
4. Переход логируется как special transition.
5. Deal Card возвращается в предыдущий статус.

---

## 19. Red flags и exceptions

### Red flags
- попытка невалидного перехода;
- попытка пропустить обязательный этап;
- попытка перейти без required artifact;
- попытка human approval transition без approval record;
- попытка сменить финальный статус без причины;
- рассинхрон между статусом Deal Card и реальным наличием артефактов.

### Exceptions
- ручная административная коррекция;
- объединение дублей;
- экстренное закрытие сделки по внешним причинам;
- спорный переход в `CLOSED_WITH_INCIDENT`.

### Как обрабатывать
- не применять переход автоматически;
- писать в журнал;
- выставлять flag manual review;
- уведомлять Chief of Staff AI и при необходимости тебя.

---

## 20. UI-требования

### В MVP нужно показать:
- текущий статус сделки;
- lifecycle stage;
- историю переходов;
- кто и когда перевел сделку;
- какой артефакт поддержал переход;
- какие следующие статусы доступны;
- если статус blocked — почему blocked.

### В таблице сделок
Показывать:
- текущий статус;
- цветовой индикатор стадии;
- stuck/overdue indicator;
- последний transition timestamp.

---

## 21. Аудит и журнал переходов

Каждый transition record должен содержать:

```json
{
  "transition_id": "TR-000001",
  "deal_id": "DL-2026-000001",
  "from_status": "ECONOMICS_REVIEW",
  "to_status": "RISK_REVIEW",
  "transition_event": "finance_memo_completed",
  "initiator_type": "AGENT",
  "initiator_id": "Pricing AI",
  "reason": "Finance review completed",
  "artifact_refs": ["finance_memo_001"],
  "created_at": "datetime",
  "is_rollback": false
}
```

---

## 22. Требования к данным

### Таблица / сущность статусов должна содержать:
- `deal_id`
- `current_status`
- `lifecycle_stage`
- `status_entered_at`
- `status_updated_at`
- `last_transition_id`
- `is_terminal`
- `is_blocked`

### Таблица / сущность переходов должна содержать:
- `transition_id`
- `deal_id`
- `from_status`
- `to_status`
- `event`
- `initiator_type`
- `initiator_id`
- `reason`
- `artifact_refs`
- `created_at`
- `is_rollback`

---

## 23. Definition of Done

Модуль считается готовым, если:

1. Есть канонический список статусов.  
2. Есть таблица допустимых переходов.  
3. Система умеет валидировать переход до его применения.  
4. Система запрещает невалидные переходы.  
5. Система умеет применять валидный переход.  
6. Каждый переход логируется в отдельную запись.  
7. Deal Card получает обновление текущего статуса.  
8. Есть поддержка human approval переходов.  
9. Есть controlled rollback.  
10. M-002 можно использовать как основу для M-004 Журнал событий и решений и M-051 Workflow Orchestrator.

---

## 24. Тест-кейсы

### Позитивные
1. `NEW_SIGNAL` → `SCREENING`
2. `SCREENING` → `CANDIDATE`
3. `TKP_COLLECTION` → `ECONOMICS_REVIEW`
4. `WAITING_CEO_APPROVAL_TO_BID` → `APPROVED_TO_BID`
5. `BID_READY_FOR_SIGN` → `BID_SUBMITTED`
6. `PAID` → `CLOSED_SUCCESS`
7. `POSTMORTEM` → `KNOWLEDGE_CAPTURED`

### Негативные
8. Попытка `SCREENING` → `BID_PREPARATION`
9. Попытка `WAITING_CEO_APPROVAL_TO_BID` → `APPROVED_TO_BID` без approval record
10. Попытка `RISK_REVIEW` → `BID_PREPARATION`
11. Попытка `KNOWLEDGE_CAPTURED` → `DOCS_ANALYSIS`
12. Попытка перехода в `ECONOMICS_REVIEW` без `tkp_set_id`
13. Попытка rollback без причины

---

## 25. ТЗ для Codex / разработчика

### Задача
Реализовать модуль `M-002 Статусная модель сделки` как state machine для Deal Card.

### Нужно сделать
1. Спроектировать канонический справочник статусов.
2. Спроектировать таблицу допустимых переходов.
3. Реализовать `validate_transition`.
4. Реализовать `apply_transition`.
5. Реализовать `transition_history`.
6. Реализовать controlled rollback.
7. Реализовать привязку переходов к required artifacts.
8. Реализовать интеграцию с Deal Card.
9. Реализовать API для orchestrator и UI.

### Ограничения
- нельзя разрешать свободные переходы между любыми статусами;
- нельзя менять статус без записи в transition log;
- нельзя делать human approval transition без explicit approval record;
- нельзя проектировать систему только под happy path;
- нужно поддержать rollback и incident-path.

### Рекомендация по реализации
Подходит реализация как отдельный state engine:
- таблица `deal_status_current`;
- таблица `deal_status_transition_log`;
- таблица `status_transition_rules`;
- таблица `status_required_artifacts` или ruleset;
- сервис-обертка для применения перехода атомарно.

Транзакционно:
1. валидируем переход;
2. проверяем required artifacts;
3. создаем transition log;
4. обновляем current status в Deal Card;
5. публикуем event.

---

## 26. Следующий модуль после завершения

После завершения `M-002` логически идет:
- **M-003 Хранилище документов**

Почему:
статусная модель уже задаст skeleton workflow, а следующий критичный слой — это формальное хранение версий документов, без которого последующие модули анализа ТЗ и контрактов будут опираться на нестабильные входы.
