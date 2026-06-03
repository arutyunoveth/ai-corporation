# Sprint 1 Technical Spec
## Модули M-001, M-002, M-003, M-004

---

## 1. Назначение документа

Этот документ — **техническое ТЗ на Sprint 1** первой волны разработки.

Sprint 1 строит **базовый каркас системы**, без которого бессмысленно делать supplier-side, finance, bid prep и submission.

В Sprint 1 реализуются модули:

- **M-001 Deal Registry**
- **M-002 Status Model Engine**
- **M-003 Document Store**
- **M-004 Event Log & Decision Journal**

---

## 2. Главная цель Sprint 1

К концу Sprint 1 система должна уметь:

1. создавать сделку как canonical entity;
2. присваивать и менять статус сделки только по правилам;
3. хранить документы и артефакты с versioning;
4. писать события и решения в единый audit trail;
5. давать downstream-модулям устойчивую базу данных и идентификаторов.

---

## 3. Что НЕ входит в Sprint 1

В Sprint 1 не делаем:

- supplier search;
- анализ ТЗ;
- RFQ;
- расчет экономики;
- UI owner-уровня как полноценный dashboard;
- notification routing;
- orchestration logic beyond minimum interfaces;
- внешние интеграции кроме самых базовых абстракций.

Sprint 1 — это **data backbone + audit backbone**.

---

## 4. Архитектурные принципы Sprint 1

### Принцип 1. Deal-first
Любой объект в системе должен уметь привязываться к `deal_id`.

### Принцип 2. Event-first
Любое значимое действие должно оставлять event trace.

### Принцип 3. Artifact-ref only
Модули не должны работать с “каким-то файлом в папке”. Только через `artifact_ref`.

### Принцип 4. Explicit status machine
Статус сделки меняется только через formal transition.

### Принцип 5. Downstream-ready schemas
Все сущности создаются не “на сейчас”, а так, чтобы их можно было использовать во 2–10 спринтах без переделки основы.

---

# 5. Границы Sprint 1 по модулям

---

# M-001 — Deal Registry

## 5.1 Назначение модуля

`M-001` — это канонический реестр сделок.  
Он отвечает за создание и хранение сущности сделки как центрального объекта всей системы.

Без него:
- downstream-модулям не к чему привязывать документы;
- нельзя строить status model;
- нельзя вести audit trail;
- нельзя строить lifecycle.

---

## 5.2 User stories

### US-001
Как система,  
я хочу создавать deal record при intake новой закупки,  
чтобы вся дальнейшая работа шла вокруг единого идентификатора сделки.

### US-002
Как downstream-модуль,  
я хочу получать canonical `deal_id`,  
чтобы связывать с ним документы, статусы, события, решения и внешние сущности.

### US-003
Как owner,  
я хочу видеть список сделок и базовую информацию по ним,  
чтобы понимать, что вообще находится в pipeline.

---

## 5.3 Основные сущности

### 1. `deal`
Главная каноническая сущность сделки.

### 2. `deal_external_refs`
Внешние ссылки и идентификаторы закупки.

### 3. `deal_tags`
Категории, labels, служебные флаги.

---

## 5.4 Таблицы

## Таблица `deals`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | Внутренний PK |
| deal_id | VARCHAR(32) | да | Канонический бизнес-ID вида `DL-2026-000001` |
| title | TEXT | да | Короткое название сделки |
| customer_name | TEXT | нет | Название заказчика |
| procurement_number | TEXT | нет | Номер закупки / извещения |
| procurement_channel | TEXT | нет | Источник: ETP, email, manual, portal |
| initial_source_type | TEXT | да | intake source type |
| direction_type | TEXT | да | Обычно `SUPPLY` |
| domain_type | TEXT | да | Например `ELECTRICAL_EQUIPMENT` |
| current_status | TEXT | да | Текущий lifecycle status |
| priority_bucket | TEXT | нет | future use |
| created_at | TIMESTAMP | да | Время создания |
| updated_at | TIMESTAMP | да | Время обновления |
| archived_at | TIMESTAMP | нет | Для будущего archive flow |
| is_deleted | BOOLEAN | да | soft delete flag, default false |

### Индексы
- unique index on `deal_id`
- index on `current_status`
- index on `created_at`
- index on `procurement_number`

---

## Таблица `deal_external_refs`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| deal_id | VARCHAR(32) | да | FK to deals.deal_id |
| ref_type | TEXT | да | `PORTAL_URL`, `ETP_ID`, `CUSTOMER_ID`, etc |
| ref_value | TEXT | да | Значение |
| created_at | TIMESTAMP | да | Дата создания |

### Индексы
- index on `deal_id`
- index on `ref_type`

---

## Таблица `deal_tags`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| deal_id | VARCHAR(32) | да | FK |
| tag_code | TEXT | да | Тег |
| created_at | TIMESTAMP | да | Дата |

### Индексы
- index on `deal_id`
- index on `tag_code`

---

## 5.5 API

### `POST /deals`
Создать сделку.

#### Request
```json
{
  "title": "Поставка автоматических выключателей",
  "customer_name": "АО Пример",
  "procurement_number": "123456789",
  "procurement_channel": "ETP",
  "initial_source_type": "portal_ingest",
  "direction_type": "SUPPLY",
  "domain_type": "ELECTRICAL_EQUIPMENT"
}
```

#### Response
```json
{
  "deal_id": "DL-2026-000001",
  "current_status": "NEW"
}
```

---

### `GET /deals/{deal_id}`
Получить сделку.

---

### `GET /deals`
Список сделок с фильтрами:
- status
- date_from/date_to
- procurement_number
- customer_name

---

### `PATCH /deals/{deal_id}`
Обновить metadata сделки.

---

## 5.6 События модуля

### Event: `deal_created`
```json
{
  "event_code": "deal_created",
  "deal_id": "DL-2026-000001",
  "payload": {
    "title": "Поставка автоматических выключателей"
  }
}
```

### Event: `deal_metadata_updated`

---

## 5.7 Acceptance criteria

1. При создании сделки формируется уникальный `deal_id`.
2. Сделка сохраняется в `deals`.
3. По `deal_id` можно получить объект сделки.
4. Изменения metadata обновляют `updated_at`.
5. Событие `deal_created` пишется в event log.
6. `current_status` создается с дефолтным статусом `NEW` или `CANDIDATE` по согласованной модели.

---

# M-002 — Status Model Engine

## 6.1 Назначение модуля

`M-002` управляет жизненным циклом сделки:
- какие статусы существуют;
- какие переходы разрешены;
- кто инициировал переход;
- когда и почему он произошел.

---

## 6.2 User stories

### US-004
Как система,  
я хочу валидировать переходы между статусами,  
чтобы сделка не перескакивала хаотично между этапами.

### US-005
Как owner,  
я хочу видеть историю смены статусов,  
чтобы понимать путь сделки и причины переходов.

### US-006
Как orchestrator,  
я хочу получать machine-readable validation результата перехода,  
чтобы route engine работал строго по статусной модели.

---

## 6.3 Основные сущности

### 1. `status_transition_rule`
Справочник разрешенных переходов.

### 2. `deal_status_history`
История смены статусов по сделке.

### 3. `manual_override_marker`
Признак, что переход сделан вручную или с override.

---

## 6.4 Таблицы

## Таблица `status_transition_rules`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| from_status | TEXT | да | Исходный статус |
| to_status | TEXT | да | Целевой статус |
| is_enabled | BOOLEAN | да | Активность правила |
| transition_type | TEXT | да | `AUTO`, `HUMAN`, `BOTH` |
| notes | TEXT | нет | Комментарий |

### Индексы
- unique index on `(from_status, to_status)`

---

## Таблица `deal_status_history`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| deal_id | VARCHAR(32) | да | FK |
| from_status | TEXT | нет | Старый статус |
| to_status | TEXT | да | Новый статус |
| changed_by_type | TEXT | да | `SYSTEM`, `HUMAN`, `MODULE` |
| changed_by_ref | TEXT | нет | module_id / agent / CEO |
| reason_code | TEXT | нет | machine-readable reason |
| reason_text | TEXT | нет | human-readable reason |
| is_override | BOOLEAN | да | override flag |
| created_at | TIMESTAMP | да | Дата перехода |

### Индексы
- index on `deal_id`
- index on `to_status`
- index on `created_at`

---

## 6.5 Минимальный статусный словарь для Sprint 1

На Sprint 1 достаточно завести базовый skeleton statuses:

- `NEW`
- `CANDIDATE`
- `DOCS_ANALYSIS`
- `SUPPLIER_SOURCING`
- `ECONOMICS_REVIEW`
- `WAITING_CEO_APPROVAL_TO_BID`
- `BID_PREPARATION`
- `PRE_SUBMISSION`
- `SUBMISSION`
- `POST_SUBMISSION`
- `OUTCOME_CAPTURE`
- `DECLINED_TO_BID`
- `REJECTED_EARLY`

Можно расширять позже, но эти нужны уже сейчас.

---

## 6.6 API

### `POST /status/validate-transition`
```json
{
  "deal_id": "DL-2026-000001",
  "from_status": "DOCS_ANALYSIS",
  "to_status": "SUPPLIER_SOURCING"
}
```

### Response
```json
{
  "allowed": true
}
```

---

### `POST /status/apply-transition`
```json
{
  "deal_id": "DL-2026-000001",
  "to_status": "SUPPLIER_SOURCING",
  "changed_by_type": "SYSTEM",
  "changed_by_ref": "M-051",
  "reason_code": "analysis_completed",
  "reason_text": "Document analysis completed",
  "is_override": false
}
```

---

### `GET /status/history/{deal_id}`

---

## 6.7 События модуля

- `deal_status_changed`
- `deal_status_transition_blocked`
- `deal_status_override_applied`

---

## 6.8 Acceptance criteria

1. Переход нельзя применить без валидации rule.
2. История переходов сохраняется в `deal_status_history`.
3. `deals.current_status` синхронизируется с последним статусом.
4. Invalid transition возвращает formal block response.
5. Override явно фиксируется.

---

# M-003 — Document Store

## 7.1 Назначение модуля

`M-003` — единое хранилище артефактов:
- тендерные документы;
- файлы поставщиков;
- generated docs;
- receipts;
- memo artifacts.

Sprint 1 делает именно **foundation storage model**.

---

## 7.2 User stories

### US-007
Как система,  
я хочу сохранять любой файл как formal artifact,  
чтобы дальше работать с ним по ref.

### US-008
Как downstream-модуль,  
я хочу получать `artifact_ref`, а не файловый хаос.

### US-009
Как owner,  
я хочу знать, какой документ к какой сделке относится и какая у него версия.

---

## 7.3 Основные сущности

### 1. `document_artifact`
Канонический файл/документ.

### 2. `artifact_versions`
История версий.

### 3. `artifact_links`
Привязки артефакта к сделке и объектам.

---

## 7.4 Таблицы

## Таблица `document_artifacts`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| artifact_ref | VARCHAR(64) | да | Уникальный ref вида `ART-2026-000001` |
| deal_id | VARCHAR(32) | нет | FK to deals.deal_id |
| artifact_type | TEXT | да | `TENDER_DOC`, `SUPPLIER_QUOTE`, `GENERATED_DOC`, etc |
| file_name | TEXT | да | Имя файла |
| mime_type | TEXT | нет | MIME |
| storage_uri | TEXT | да | Путь/URI |
| checksum_sha256 | TEXT | нет | Хэш |
| current_version | INTEGER | да | Текущая версия |
| created_at | TIMESTAMP | да | Дата |
| updated_at | TIMESTAMP | да | Дата |

### Индексы
- unique index on `artifact_ref`
- index on `deal_id`
- index on `artifact_type`

---

## Таблица `artifact_versions`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| artifact_ref | VARCHAR(64) | да | FK |
| version_no | INTEGER | да | Версия |
| storage_uri | TEXT | да | URI версии |
| checksum_sha256 | TEXT | нет | Хэш |
| created_at | TIMESTAMP | да | Дата |

### Индексы
- unique index on `(artifact_ref, version_no)`

---

## Таблица `artifact_links`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| artifact_ref | VARCHAR(64) | да | FK |
| linked_object_type | TEXT | да | `DEAL`, `QUOTE`, `MEMO`, etc |
| linked_object_ref | TEXT | да | `DL-...`, `Q-...`, etc |
| created_at | TIMESTAMP | да | Дата |

### Индексы
- index on `artifact_ref`
- index on `(linked_object_type, linked_object_ref)`

---

## 7.5 API

### `POST /artifacts`
Создать artifact.

### `POST /artifacts/{artifact_ref}/versions`
Добавить новую версию.

### `GET /artifacts/{artifact_ref}`
Получить artifact meta.

### `GET /artifacts/{artifact_ref}/versions`
Получить версии.

### `POST /artifacts/{artifact_ref}/links`
Добавить link.

---

## 7.6 Acceptance criteria

1. Любой документ можно сохранить как artifact.
2. Artifact имеет уникальный `artifact_ref`.
3. Версии поддерживаются.
4. Можно link-нуть artifact к deal.
5. Storage model не зависит от конкретного UI.

---

# M-004 — Event Log & Decision Journal

## 8.1 Назначение модуля

`M-004` — audit backbone всей компании.

Он хранит:
- события модулей;
- решения человека;
- блокировки;
- overrides;
- служебные runtime markers.

---

## 8.2 User stories

### US-010
Как система,  
я хочу писать business and runtime events into one log.

### US-011
Как owner,  
я хочу видеть, какие события и решения происходили по сделке.

### US-012
Как future observability layer,  
я хочу искать audit trace по deal/module/event type.

---

## 8.3 Основные сущности

### 1. `event_record`
Machine-readable event.

### 2. `decision_record`
Human/system decision with rationale.

### 3. `event_payload_archive`
Raw payload storage, если нужен.

---

## 8.4 Таблицы

## Таблица `event_records`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| event_id | VARCHAR(64) | да | Уникальный event ref |
| deal_id | VARCHAR(32) | нет | FK |
| event_code | TEXT | да | Код события |
| source_module_id | TEXT | нет | M-xxx |
| source_agent_code | TEXT | нет | agent code |
| severity | TEXT | да | `INFO`, `WARNING`, `HIGH`, `CRITICAL` |
| payload_json | JSONB / TEXT | нет | Структурированный payload |
| created_at | TIMESTAMP | да | Дата |

### Индексы
- unique index on `event_id`
- index on `deal_id`
- index on `event_code`
- index on `source_module_id`
- index on `created_at`

---

## Таблица `decision_records`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| decision_id | VARCHAR(64) | да | Ref |
| deal_id | VARCHAR(32) | да | FK |
| decision_code | TEXT | да | `APPROVE_TO_BID`, `DECLINE_TO_BID`, etc |
| decided_by_type | TEXT | да | `HUMAN`, `SYSTEM` |
| decided_by_ref | TEXT | нет | CEO / module |
| rationale | TEXT | нет | Причина |
| payload_json | JSONB / TEXT | нет | Доп. данные |
| created_at | TIMESTAMP | да | Дата |

### Индексы
- unique index on `decision_id`
- index on `deal_id`
- index on `decision_code`

---

## 8.5 API

### `POST /events`
```json
{
  "deal_id": "DL-2026-000001",
  "event_code": "deal_created",
  "source_module_id": "M-001",
  "severity": "INFO",
  "payload_json": {
    "title": "Поставка автоматических выключателей"
  }
}
```

### `POST /decisions`
```json
{
  "deal_id": "DL-2026-000001",
  "decision_code": "APPROVE_TO_BID",
  "decided_by_type": "HUMAN",
  "decided_by_ref": "CEO",
  "rationale": "Economics acceptable"
}
```

### `GET /events?deal_id=DL-2026-000001`
### `GET /decisions?deal_id=DL-2026-000001`

---

## 8.6 Acceptance criteria

1. Любой модуль может append event.
2. Human decision записывается как separate formal record.
3. Events searchable by deal/module/event code.
4. Decisions searchable by deal.
5. Log пригоден для future observability and audit console.

---

# 9. Межмодульные контракты Sprint 1

## 9.1 Обязательные shared identifiers

Во всех модулях Sprint 1 должны использоваться единообразно:

- `deal_id`
- `artifact_ref`
- `event_id`
- `decision_id`

---

## 9.2 Базовые event codes Sprint 1

Минимальный набор:

- `deal_created`
- `deal_metadata_updated`
- `deal_status_changed`
- `deal_status_transition_blocked`
- `artifact_created`
- `artifact_version_added`
- `artifact_linked`
- `decision_recorded`

---

## 9.3 Базовые decision codes Sprint 1

На Sprint 1 минимум:
- `MANUAL_STATUS_OVERRIDE`
- `DEAL_MARKED_REJECTED_EARLY`

---

# 10. Нефункциональные требования Sprint 1

## 10.1 Auditability
Любая операция create/update/transition должна быть traceable.

## 10.2 Idempotency
Повторный create/update по безопасным операциям не должен создавать хаос.

## 10.3 Soft delete only
Никаких hard delete бизнес-сущностей в Sprint 1.

## 10.4 UTC timestamps
Все временные поля сохраняются в UTC.

## 10.5 Schema-first
Все payload contracts фиксируются в code + docs явно.

---

# 11. Порядок реализации внутри Sprint 1

## Шаг 1
Схемы таблиц:
- deals
- deal_external_refs
- deal_tags
- status_transition_rules
- deal_status_history
- document_artifacts
- artifact_versions
- artifact_links
- event_records
- decision_records

## Шаг 2
CRUD/API:
- M-001
- M-003
- M-004

## Шаг 3
Status engine:
- rules seed
- validation
- apply transition

## Шаг 4
Cross-module linking:
- create deal → write event
- create artifact → link to deal → write event
- apply transition → update deal status → write event

## Шаг 5
Minimal admin/dev views:
- deals list
- deal detail
- artifact list by deal
- event history by deal
- status history by deal

---

# 12. Acceptance criteria по всему Sprint 1

Sprint 1 завершен, если:

1. можно создать сделку и получить canonical `deal_id`;
2. можно сохранить артефакт и получить `artifact_ref`;
3. можно link-нуть artifact to deal;
4. можно менять статус только по правилам;
5. история переходов сохраняется;
6. события пишутся в единый event log;
7. решения пишутся в decision journal;
8. по deal можно собрать:
   - metadata,
   - current status,
   - status history,
   - linked artifacts,
   - audit trail.

---

# 13. Что делать сразу после Sprint 1

После Sprint 1 надо идти в **Sprint 2 Technical Spec** и описывать:

- M-051 runtime completion details, если сделан только skeleton;
- M-055 minimum connectors;
- M-052 minimum notifications;
- M-008 / M-011 / M-012 intake path.

Но переходить туда стоит только когда Sprint 1:
- стабилен по entity model;
- не вызывает споров по ключевым IDs;
- не требует пересборки базовых схем.

---

# 14. Итог

Sprint 1 — это не “техническая рутина”.  
Это фундамент всей компании.

Если его сделать аккуратно:
- downstream-модули будут стыковаться легче;
- Codex не начнет плодить несовместимые сущности;
- audit и trace не придется доделывать задним числом;
- система будет расширяться без архитектурного хаоса.
