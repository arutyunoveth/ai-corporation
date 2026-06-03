# Entity Catalog Sprint 1
## Модули M-001, M-002, M-003, M-004

---

## 1. Назначение документа

Этот документ — **единый каталог сущностей Sprint 1**.

Он нужен как bridge между:
- архитектурным ТЗ;
- Sprint 1 Technical Spec;
- реальной генерацией кода в Codex;
- проектированием БД, DTO, API contracts и event schemas.

### Задача каталога
Зафиксировать:
- canonical entities;
- их поля;
- идентификаторы;
- enums;
- связи;
- инварианты;
- минимальные migration rules;
- naming conventions.

---

## 2. Границы каталога

Каталог покрывает только Sprint 1:

- **M-001 Deal Registry**
- **M-002 Status Model Engine**
- **M-003 Document Store**
- **M-004 Event Log & Decision Journal**

Он не описывает downstream-сущности supplier-side, finance, bid prep и execution, кроме тех полей и ref-правил, которые нужны уже сейчас для совместимости.

---

## 3. Общие правила моделирования

## 3.1 Главные идентификаторы

В Sprint 1 используются 4 канонических business IDs:

- `deal_id`
- `artifact_ref`
- `event_id`
- `decision_id`

Это **публичные системные идентификаторы** для бизнес-логики и межмодульных контрактов.

Внутри БД можно использовать:
- `id` как UUID или BIGINT PK,
но снаружи модули должны опираться на **canonical refs**.

---

## 3.2 Форматы идентификаторов

### `deal_id`
Формат:
```text
DL-YYYY-NNNNNN
```

Пример:
```text
DL-2026-000001
```

### `artifact_ref`
Формат:
```text
ART-YYYY-NNNNNN
```

Пример:
```text
ART-2026-000001
```

### `event_id`
Формат:
```text
EVT-YYYY-NNNNNN
```

### `decision_id`
Формат:
```text
DEC-YYYY-NNNNNN
```

### Требование
Генерация canonical IDs должна быть:
- уникальной;
- deterministic enough at storage layer;
- централизованной;
- не зависеть от UI.

---

## 3.3 Базовые типы полей

Рекомендуемые типы:

- IDs: `VARCHAR(32..64)` for business refs
- PK: `UUID` или `BIGINT`
- timestamps: `TIMESTAMP WITH TIME ZONE` / UTC
- JSON payloads: `JSONB`
- codes/enums: `TEXT` + validation layer
- long descriptions/rationales: `TEXT`

---

## 3.4 Общие инварианты

### Инвариант 1
Любая downstream сущность обязана уметь хранить `deal_id`, если относится к сделке.

### Инвариант 2
Никакая бизнес-сущность не удаляется hard delete в Sprint 1.

### Инвариант 3
Любая существенная операция должна оставлять запись в event log.

### Инвариант 4
Изменение статуса не может происходить “мимо” status engine.

### Инвариант 5
Работа с файлами идет только через `artifact_ref`.

---

# 4. Entity Catalog — M-001 Deal Registry

## 4.1 Сущность `deal`

### Назначение
Канонический объект сделки.

### Бизнес-смысл
Это центр всей системы. Все остальные сущности либо:
- принадлежат сделке;
- описывают состояние сделки;
- документируют действия вокруг сделки.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | Внутренний PK |
| deal_id | VARCHAR(32) | нет | Канонический business ID |
| title | TEXT | нет | Рабочее название сделки |
| customer_name | TEXT | да | Название заказчика |
| procurement_number | TEXT | да | Номер закупки |
| procurement_channel | TEXT | да | Канал: ETP / portal / email / manual |
| initial_source_type | TEXT | нет | Тип источника intake |
| direction_type | TEXT | нет | Тип направления, напр. `SUPPLY` |
| domain_type | TEXT | нет | Домен, напр. `ELECTRICAL_EQUIPMENT` |
| current_status | TEXT | нет | Текущий lifecycle status |
| priority_bucket | TEXT | да | Зарезервировано под scoring |
| created_at | TIMESTAMP UTC | нет | Время создания |
| updated_at | TIMESTAMP UTC | нет | Время обновления |
| archived_at | TIMESTAMP UTC | да | Для будущего archive branch |
| is_deleted | BOOLEAN | нет | Soft delete flag |

### Инварианты
- `deal_id` unique
- `title` required
- `current_status` required
- `created_at` and `updated_at` always set
- `is_deleted = false` by default

### Индексы
- unique(`deal_id`)
- index(`current_status`)
- index(`created_at`)
- index(`procurement_number`)

---

## 4.2 Сущность `deal_external_ref`

### Назначение
Хранит внешние идентификаторы и ссылки закупки.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| deal_id | VARCHAR(32) | нет | FK to deal.deal_id |
| ref_type | TEXT | нет | Тип ссылки |
| ref_value | TEXT | нет | Значение ссылки |
| created_at | TIMESTAMP UTC | нет | Дата создания |

### Примеры `ref_type`
- `PORTAL_URL`
- `ETP_ID`
- `CUSTOMER_ID`
- `NOTICE_URL`
- `INTERNAL_IMPORT_ID`

### Инварианты
- `deal_id` must exist in `deal`
- one deal can have many external refs

### Индексы
- index(`deal_id`)
- index(`ref_type`)

---

## 4.3 Сущность `deal_tag`

### Назначение
Легковесные labels и служебные теги.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| deal_id | VARCHAR(32) | нет | FK |
| tag_code | TEXT | нет | Тег |
| created_at | TIMESTAMP UTC | нет | Дата |

### Примеры `tag_code`
- `HIGH_PRIORITY`
- `MANUAL_REVIEW`
- `COMPLEX_PROCUREMENT`
- `ELECTRICAL_SCOPE`

---

# 5. Entity Catalog — M-002 Status Model Engine

## 5.1 Сущность `status_transition_rule`

### Назначение
Справочник allowed transitions.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| from_status | TEXT | нет | Исходный статус |
| to_status | TEXT | нет | Целевой статус |
| is_enabled | BOOLEAN | нет | Активность правила |
| transition_type | TEXT | нет | `AUTO`, `HUMAN`, `BOTH` |
| notes | TEXT | да | Комментарий |
| created_at | TIMESTAMP UTC | нет | Дата |
| updated_at | TIMESTAMP UTC | нет | Дата |

### Инварианты
- pair (`from_status`, `to_status`) unique
- disabled rule cannot validate transition

### Индексы
- unique(`from_status`, `to_status`)

---

## 5.2 Сущность `deal_status_history`

### Назначение
История смены статусов по сделке.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| deal_id | VARCHAR(32) | нет | FK |
| from_status | TEXT | да | Предыдущий статус |
| to_status | TEXT | нет | Новый статус |
| changed_by_type | TEXT | нет | `SYSTEM`, `HUMAN`, `MODULE`, `AGENT` |
| changed_by_ref | TEXT | да | Кто сменил |
| reason_code | TEXT | да | Machine-readable reason |
| reason_text | TEXT | да | Human-readable explanation |
| is_override | BOOLEAN | нет | Был ли override |
| created_at | TIMESTAMP UTC | нет | Время перехода |

### Инварианты
- `to_status` required
- `deal_id` must exist
- `created_at` immutable
- history append-only

### Индексы
- index(`deal_id`)
- index(`to_status`)
- index(`created_at`)

---

## 5.3 Derived rule: `deal.current_status`

`deal.current_status` — это **derived current state**, который:
- обновляется при успешном `apply_transition`
- должен совпадать с последней записью `deal_status_history.to_status`

### Инвариант синхронизации
For every deal:
- latest history row `to_status` == `deal.current_status`

---

# 6. Entity Catalog — M-003 Document Store

## 6.1 Сущность `document_artifact`

### Назначение
Канонический объект артефакта/документа.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| artifact_ref | VARCHAR(64) | нет | Канонический ref |
| deal_id | VARCHAR(32) | да | FK to deal |
| artifact_type | TEXT | нет | Тип артефакта |
| file_name | TEXT | нет | Имя файла |
| mime_type | TEXT | да | MIME |
| storage_uri | TEXT | нет | URI / path |
| checksum_sha256 | TEXT | да | Хэш |
| current_version | INTEGER | нет | Текущая версия |
| created_at | TIMESTAMP UTC | нет | Дата |
| updated_at | TIMESTAMP UTC | нет | Дата |

### Примеры `artifact_type`
- `TENDER_DOC`
- `SUPPLIER_QUOTE`
- `GENERATED_DOC`
- `RECEIPT_DOC`
- `MEMO_ARTIFACT`
- `ATTACHMENT`

### Инварианты
- `artifact_ref` unique
- `current_version >= 1`
- `storage_uri` required
- `file_name` required

### Индексы
- unique(`artifact_ref`)
- index(`deal_id`)
- index(`artifact_type`)

---

## 6.2 Сущность `artifact_version`

### Назначение
История версий артефакта.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| artifact_ref | VARCHAR(64) | нет | FK to artifact |
| version_no | INTEGER | нет | Номер версии |
| storage_uri | TEXT | нет | URI версии |
| checksum_sha256 | TEXT | да | Хэш |
| created_at | TIMESTAMP UTC | нет | Дата |

### Инварианты
- `(artifact_ref, version_no)` unique
- first version must be `1`
- current artifact.current_version must point to highest version_no

---

## 6.3 Сущность `artifact_link`

### Назначение
Привязка артефакта к объектам системы.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| artifact_ref | VARCHAR(64) | нет | FK |
| linked_object_type | TEXT | нет | Тип объекта |
| linked_object_ref | TEXT | нет | Ref объекта |
| created_at | TIMESTAMP UTC | нет | Дата |

### Примеры `linked_object_type`
- `DEAL`
- `STATUS_HISTORY`
- `EVENT`
- `DECISION`
- future: `QUOTE`, `MEMO`, `PACKAGE`

### Инварианты
- one artifact may have many links
- link rows append-only unless explicit admin repair
- `linked_object_ref` is business ref, not internal PK

---

# 7. Entity Catalog — M-004 Event Log & Decision Journal

## 7.1 Сущность `event_record`

### Назначение
Machine-readable event record.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| event_id | VARCHAR(64) | нет | Canonical event ref |
| deal_id | VARCHAR(32) | да | FK to deal |
| event_code | TEXT | нет | Код события |
| source_module_id | TEXT | да | Например `M-001` |
| source_agent_code | TEXT | да | Agent code if applicable |
| severity | TEXT | нет | Уровень значимости |
| payload_json | JSONB | да | Event payload |
| created_at | TIMESTAMP UTC | нет | Время |

### Базовые значения `severity`
- `INFO`
- `WARNING`
- `HIGH`
- `CRITICAL`

### Инварианты
- `event_id` unique
- `event_code` required
- payload may be null, but event shell must exist
- append-only

### Индексы
- unique(`event_id`)
- index(`deal_id`)
- index(`event_code`)
- index(`source_module_id`)
- index(`created_at`)

---

## 7.2 Сущность `decision_record`

### Назначение
Formal record human/system decision.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| decision_id | VARCHAR(64) | нет | Canonical decision ref |
| deal_id | VARCHAR(32) | нет | FK |
| decision_code | TEXT | нет | Код решения |
| decided_by_type | TEXT | нет | `HUMAN`, `SYSTEM`, `MODULE` |
| decided_by_ref | TEXT | да | CEO, module ID, etc |
| rationale | TEXT | да | Обоснование |
| payload_json | JSONB | да | Structured add-ons |
| created_at | TIMESTAMP UTC | нет | Время |

### Инварианты
- `decision_id` unique
- `deal_id` required
- append-only
- business-significant decision should have either rationale or payload

### Индексы
- unique(`decision_id`)
- index(`deal_id`)
- index(`decision_code`)

---

# 8. Enums и reference dictionaries Sprint 1

## 8.1 Enum `DealStatus`

```text
NEW
CANDIDATE
DOCS_ANALYSIS
SUPPLIER_SOURCING
ECONOMICS_REVIEW
WAITING_CEO_APPROVAL_TO_BID
BID_PREPARATION
PRE_SUBMISSION
SUBMISSION
POST_SUBMISSION
OUTCOME_CAPTURE
DECLINED_TO_BID
REJECTED_EARLY
```

---

## 8.2 Enum `TransitionType`

```text
AUTO
HUMAN
BOTH
```

---

## 8.3 Enum `ChangedByType`

```text
SYSTEM
HUMAN
MODULE
AGENT
```

---

## 8.4 Enum `ArtifactType`

```text
TENDER_DOC
SUPPLIER_QUOTE
GENERATED_DOC
RECEIPT_DOC
MEMO_ARTIFACT
ATTACHMENT
OTHER
```

---

## 8.5 Enum `EventSeverity`

```text
INFO
WARNING
HIGH
CRITICAL
```

---

## 8.6 Enum `DecisionByType`

```text
HUMAN
SYSTEM
MODULE
```

---

## 8.7 Enum `ProcurementChannel`

```text
ETP
PORTAL
EMAIL
MANUAL
OTHER
```

---

## 8.8 Enum `DirectionType`

```text
SUPPLY
```

На Sprint 1 достаточно зафиксировать именно supply domain.

---

## 8.9 Enum `InitialSourceType`

```text
portal_ingest
email_ingest
manual_entry
api_import
other
```

---

# 9. Межсущностные связи

## 9.1 Deal-centric graph

```text
deal
 ├─ deal_external_ref [1..N]
 ├─ deal_tag [0..N]
 ├─ deal_status_history [0..N]
 ├─ document_artifact [0..N]
 ├─ event_record [0..N]
 └─ decision_record [0..N]
```

---

## 9.2 Artifact-centric graph

```text
document_artifact
 ├─ artifact_version [1..N]
 └─ artifact_link [0..N]
```

---

## 9.3 Status-centric graph

```text
status_transition_rule
deal_status_history
deal.current_status (derived current state)
```

---

# 10. API DTO contracts

## 10.1 CreateDealRequest

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

## 10.2 CreateDealResponse

```json
{
  "deal_id": "DL-2026-000001",
  "current_status": "NEW",
  "created_at": "2026-06-03T10:00:00Z"
}
```

---

## 10.3 ApplyTransitionRequest

```json
{
  "deal_id": "DL-2026-000001",
  "to_status": "DOCS_ANALYSIS",
  "changed_by_type": "SYSTEM",
  "changed_by_ref": "M-051",
  "reason_code": "intake_completed",
  "reason_text": "Deal moved into docs analysis after intake",
  "is_override": false
}
```

---

## 10.4 CreateArtifactRequest

```json
{
  "deal_id": "DL-2026-000001",
  "artifact_type": "TENDER_DOC",
  "file_name": "specification.pdf",
  "mime_type": "application/pdf",
  "storage_uri": "s3://bucket/specification.pdf",
  "checksum_sha256": "abc123"
}
```

---

## 10.5 AppendEventRequest

```json
{
  "deal_id": "DL-2026-000001",
  "event_code": "deal_created",
  "source_module_id": "M-001",
  "source_agent_code": null,
  "severity": "INFO",
  "payload_json": {
    "title": "Поставка автоматических выключателей"
  }
}
```

---

## 10.6 AppendDecisionRequest

```json
{
  "deal_id": "DL-2026-000001",
  "decision_code": "MANUAL_STATUS_OVERRIDE",
  "decided_by_type": "HUMAN",
  "decided_by_ref": "CEO",
  "rationale": "Manual correction after wrong status route",
  "payload_json": {
    "from_status": "DOCS_ANALYSIS",
    "to_status": "CANDIDATE"
  }
}
```

---

# 11. Базовые event codes Sprint 1

Минимальный справочник:

```text
deal_created
deal_metadata_updated
deal_status_changed
deal_status_transition_blocked
deal_status_override_applied
artifact_created
artifact_version_added
artifact_linked
decision_recorded
```

---

# 12. Базовые decision codes Sprint 1

```text
MANUAL_STATUS_OVERRIDE
DEAL_MARKED_REJECTED_EARLY
```

---

# 13. Migration order

Чтобы Codex не породил циклический хаос, миграции надо делать так:

## Migration 001
- `deals`
- `deal_external_refs`
- `deal_tags`

## Migration 002
- `status_transition_rules`
- `deal_status_history`

## Migration 003
- `document_artifacts`
- `artifact_versions`
- `artifact_links`

## Migration 004
- `event_records`
- `decision_records`

## Migration 005
- seed `status_transition_rules`
- seed enum dictionaries if you keep them in DB

---

# 14. Seed data Sprint 1

## 14.1 Status transition seeds

Минимально рекомендованные transitions:

```text
NEW -> CANDIDATE
CANDIDATE -> DOCS_ANALYSIS
CANDIDATE -> REJECTED_EARLY
DOCS_ANALYSIS -> SUPPLIER_SOURCING
DOCS_ANALYSIS -> REJECTED_EARLY
SUPPLIER_SOURCING -> ECONOMICS_REVIEW
ECONOMICS_REVIEW -> WAITING_CEO_APPROVAL_TO_BID
WAITING_CEO_APPROVAL_TO_BID -> BID_PREPARATION
WAITING_CEO_APPROVAL_TO_BID -> DECLINED_TO_BID
BID_PREPARATION -> PRE_SUBMISSION
PRE_SUBMISSION -> SUBMISSION
SUBMISSION -> POST_SUBMISSION
POST_SUBMISSION -> OUTCOME_CAPTURE
```

---

# 15. Validation rules

## 15.1 Deal validation
- `title` non-empty
- `direction_type` required
- `initial_source_type` required

## 15.2 Transition validation
- rule must exist and be enabled
- `deal.current_status` must match requested `from_status` if provided

## 15.3 Artifact validation
- `storage_uri` required
- `artifact_type` required
- `file_name` required

## 15.4 Event validation
- `event_code` required
- `severity` in enum
- at least one of `deal_id`, `source_module_id`, `source_agent_code` should exist

## 15.5 Decision validation
- `decision_code` required
- `deal_id` required
- `decided_by_type` required

---

# 16. Anti-chaos rules for Codex / developer

1. Do not invent new entity names if equivalent already exists in this catalog.
2. Do not use raw internal PKs in external API if canonical ref already exists.
3. Do not mutate history tables in place.
4. Do not create direct file paths in business logic; use `artifact_ref`.
5. Do not change deal status outside status engine.
6. Do not write business-significant actions without event records.

---

# 17. Minimum repository structure recommendation

```text
src/
  modules/
    deal_registry/
    status_engine/
    document_store/
    event_log/
  shared/
    ids/
    enums/
    db/
    events/
    api/
docs/
  00_architecture/
  01_sprints/
  02_entities/
```

---

# 18. What Codex should generate first

На основе этого каталога Codex должен сначала сгенерировать:

1. `shared/enums`
2. `shared/id_generators`
3. DB migrations for Sprint 1
4. ORM models / SQL schema
5. DTOs for public API
6. services for:
   - create deal
   - validate/apply transition
   - create artifact/version/link
   - append event / append decision
7. integration tests for entity invariants

---

# 19. Acceptance criteria по Entity Catalog

Каталог считается пригодным к старту кодинга, если:
1. у всех Sprint 1 сущностей есть canonical names;
2. у всех критичных refs есть format;
3. enums зафиксированы;
4. связи между сущностями понятны;
5. migration order понятен;
6. нет двусмысленности, что является source of truth.

---

# 20. Итог

Этот документ — точка, после которой Codex уже можно использовать не как “генератор идей”, а как **генератор конкретной реализации**.

Он фиксирует:
- на чем строится Sprint 1;
- какие сущности нельзя разъезжать;
- какие IDs, enums и relations обязательны;
- как защититься от архитектурного расползания на старте.
