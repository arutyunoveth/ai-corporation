
# Entity Catalog Sprint 2
## Модули M-008, M-011, M-012

---

## 1. Назначение документа

Этот документ — **единый каталог сущностей Sprint 2A**.

Он нужен как bridge между:
- Sprint 2 Technical Spec,
- текущим кодом Sprint 1,
- DB migrations,
- DTO contracts,
- сервисами intake/document ingestion/summary,
- дальнейшей генерацией кода в Codex.

---

## 2. Scope каталога

Каталог покрывает только:

- **M-008 Tender Intake Pipeline**
- **M-011 Document Ingestion Layer**
- **M-012 Tender Summary Builder**

И опирается на уже существующие сущности Sprint 1:
- `deal`
- `document_artifact`
- `event_record`
- `decision_record`

---

## 3. Общие правила Sprint 2A

## 3.1 Canonical refs Sprint 2A

Новые business IDs:

- `intake_id`
- `document_set_id`
- `ingestion_run_id`
- `tender_summary_id`

Форматы:

### `intake_id`
```text
INT-YYYY-NNNNNN
```

### `document_set_id`
```text
DS-YYYY-NNNNNN
```

### `ingestion_run_id`
```text
DIR-YYYY-NNNNNN
```

### `tender_summary_id`
```text
TS-YYYY-NNNNNN
```

---

## 3.2 Общие инварианты Sprint 2A

### Инвариант 1
Любая сущность Sprint 2A должна быть связана с `deal_id`.

### Инвариант 2
Любая сущность intake/document/summary должна оставлять event trace в M-004.

### Инвариант 3
M-011 работает только с existing `artifact_ref`, а не с raw file paths in business logic.

### Инвариант 4
Summary строится на explicit `document_set_id`, а не на случайном наборе artifacts.

### Инвариант 5
Raw intake payload должен сохраняться отдельно от canonical deal metadata.

---

# 4. Entity Catalog — M-008 Tender Intake Pipeline

## 4.1 Сущность `tender_intake_record`

### Назначение
Formal запись о факте входа закупки в систему.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| intake_id | VARCHAR(64) | нет | Canonical intake ref |
| deal_id | VARCHAR(32) | нет | FK to deals.deal_id |
| source_type | TEXT | нет | Тип источника |
| source_channel | TEXT | нет | Канал intake |
| source_title | TEXT | нет | Название из raw input |
| source_customer_name | TEXT | нет | Заказчик из raw input |
| source_procurement_number | TEXT | да | Номер закупки |
| intake_status | TEXT | нет | Статус intake |
| duplicate_hint | BOOLEAN | нет | Soft hint on likely duplicate |
| received_at | TIMESTAMP UTC | нет | Когда input получен |
| normalized_at | TIMESTAMP UTC | нет | Когда нормализован |
| created_at | TIMESTAMP UTC | нет | Дата |
| updated_at | TIMESTAMP UTC | нет | Дата |

### Инварианты
- `intake_id` unique
- `deal_id` required
- `source_type` required
- `source_channel` required
- `source_title` required
- `intake_status` required

### Индексы
- unique(`intake_id`)
- index(`deal_id`)
- index(`source_type`)
- index(`source_procurement_number`)
- index(`received_at`)

---

## 4.2 Сущность `tender_source_payload`

### Назначение
Хранит нормализованный raw payload intake, не смешивая его с canonical deal fields.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| intake_id | VARCHAR(64) | нет | FK to tender_intake_records.intake_id |
| payload_json | JSONB | нет | Нормализованный payload |
| payload_hash | TEXT | нет | Хэш полезной нагрузки |
| created_at | TIMESTAMP UTC | нет | Дата |

### Инварианты
- `payload_json` required
- `payload_hash` required
- one intake may have one or many payload snapshots in future, but Sprint 2A can keep one-per-intake policy if simpler

### Индексы
- index(`intake_id`)
- index(`payload_hash`)

---

## 4.3 Enum `TenderSourceType`

```text
PORTAL
EMAIL
MANUAL
API
OTHER
```

## 4.4 Enum `IntakeStatus`

```text
RECEIVED
NORMALIZED
LINKED
FAILED
```

---

# 5. Entity Catalog — M-011 Document Ingestion Layer

## 5.1 Сущность `document_set`

### Назначение
Канонический набор документов сделки на intake stage.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| document_set_id | VARCHAR(64) | нет | Canonical set ref |
| deal_id | VARCHAR(32) | нет | FK to deals.deal_id |
| intake_id | VARCHAR(64) | нет | FK to tender_intake_records.intake_id |
| set_type | TEXT | нет | Тип набора |
| ingestion_status | TEXT | нет | Статус ingest |
| item_count | INTEGER | нет | Count of linked items |
| created_at | TIMESTAMP UTC | нет | Дата |
| updated_at | TIMESTAMP UTC | нет | Дата |

### Инварианты
- `document_set_id` unique
- `deal_id` required
- `intake_id` required
- `item_count >= 0`
- `ingestion_status` required

### Индексы
- unique(`document_set_id`)
- index(`deal_id`)
- index(`intake_id`)
- index(`ingestion_status`)

---

## 5.2 Сущность `document_set_item`

### Назначение
Состав набора документов.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| document_set_id | VARCHAR(64) | нет | FK |
| artifact_ref | VARCHAR(64) | нет | FK to document_artifacts.artifact_ref |
| item_role | TEXT | нет | Роль документа в наборе |
| source_file_name | TEXT | нет | Имя файла |
| sort_order | INTEGER | нет | Порядок |
| created_at | TIMESTAMP UTC | нет | Дата |

### Инварианты
- `artifact_ref` must exist in document store
- `document_set_id` must exist
- `item_role` required
- `sort_order >= 0`
- same artifact may appear once per set unless future policy says otherwise

### Индексы
- index(`document_set_id`)
- index(`artifact_ref`)
- index(`item_role`)

---

## 5.3 Сущность `document_ingestion_run`

### Назначение
Трассировка отдельного run ingestion process.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| ingestion_run_id | VARCHAR(64) | нет | Canonical ref |
| document_set_id | VARCHAR(64) | нет | FK |
| run_status | TEXT | нет | Статус run |
| started_at | TIMESTAMP UTC | нет | Start |
| finished_at | TIMESTAMP UTC | да | Finish |
| notes | TEXT | да | Notes / error summary |

### Инварианты
- `ingestion_run_id` unique
- `document_set_id` required
- `run_status` required
- `finished_at >= started_at` if finished_at exists

### Индексы
- unique(`ingestion_run_id`)
- index(`document_set_id`)
- index(`run_status`)

---

## 5.4 Enum `DocumentSetType`

```text
TENDER_INITIAL
TENDER_REFRESH
OTHER
```

## 5.5 Enum `DocumentIngestionStatus`

```text
CREATED
INGESTED
PARTIAL
FAILED
```

## 5.6 Enum `DocumentIngestionRunStatus`

```text
STARTED
COMPLETED
FAILED
PARTIAL
```

## 5.7 Enum `DocumentSetItemRole`

```text
NOTICE
TZ
DRAFT_CONTRACT
ATTACHMENT
OTHER
```

---

# 6. Entity Catalog — M-012 Tender Summary Builder

## 6.1 Сущность `tender_summary`

### Назначение
Formal persisted summary of the tender.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| tender_summary_id | VARCHAR(64) | нет | Canonical ref |
| deal_id | VARCHAR(32) | нет | FK |
| intake_id | VARCHAR(64) | нет | FK |
| document_set_id | VARCHAR(64) | нет | FK |
| summary_status | TEXT | нет | Статус summary |
| summary_text | TEXT | нет | Human-readable text |
| structured_summary_json | JSONB | нет | Machine-readable summary |
| created_at | TIMESTAMP UTC | нет | Дата |
| updated_at | TIMESTAMP UTC | нет | Дата |

### Инварианты
- `tender_summary_id` unique
- `deal_id`, `intake_id`, `document_set_id` required
- `summary_text` required
- `structured_summary_json` required
- `summary_status` required

### Индексы
- unique(`tender_summary_id`)
- index(`deal_id`)
- index(`intake_id`)
- index(`document_set_id`)
- index(`summary_status`)

---

## 6.2 Сущность `tender_summary_source_link`

### Назначение
Трассировка, на основе чего была построена summary.

### Поля

| Поле | Тип | Null | Описание |
|---|---|---:|---|
| id | UUID/BIGINT | нет | PK |
| tender_summary_id | VARCHAR(64) | нет | FK |
| source_object_type | TEXT | нет | Тип исходного объекта |
| source_object_ref | TEXT | нет | Ref объекта |
| created_at | TIMESTAMP UTC | нет | Дата |

### Примеры `source_object_type`
- `DEAL`
- `INTAKE`
- `DOCUMENT_SET`
- `ARTIFACT`

### Инварианты
- one summary may have many source links
- source links append-only
- all summary builds should at minimum link:
  - deal
  - intake
  - document_set

### Индексы
- index(`tender_summary_id`)
- index(`source_object_type`, `source_object_ref`)

---

## 6.3 Enum `TenderSummaryStatus`

```text
BUILT
FAILED
STALE
```

---

# 7. Structured DTO contracts Sprint 2A

## 7.1 `CreateTenderIntakeRequest`

```json
{
  "source_type": "MANUAL",
  "source_channel": "owner_manual_entry",
  "source_title": "Поставка автоматических выключателей",
  "source_customer_name": "АО Пример",
  "source_procurement_number": "123456789",
  "payload_json": {
    "portal_url": "https://example.com/tender/123",
    "notice_date": "2026-06-03"
  },
  "initial_source_type": "manual_entry",
  "direction_type": "SUPPLY",
  "domain_type": "ELECTRICAL_EQUIPMENT"
}
```

## 7.2 `CreateTenderIntakeResponse`

```json
{
  "intake_id": "INT-2026-000001",
  "deal_id": "DL-2026-000001",
  "intake_status": "LINKED"
}
```

---

## 7.3 `CreateDocumentSetRequest`

```json
{
  "deal_id": "DL-2026-000001",
  "intake_id": "INT-2026-000001",
  "set_type": "TENDER_INITIAL",
  "items": [
    {
      "artifact_ref": "ART-2026-000001",
      "item_role": "NOTICE",
      "source_file_name": "notice.pdf",
      "sort_order": 1
    }
  ]
}
```

## 7.4 `CreateDocumentSetResponse`

```json
{
  "document_set_id": "DS-2026-000001",
  "ingestion_status": "INGESTED",
  "item_count": 1
}
```

---

## 7.5 `BuildTenderSummaryRequest`

```json
{
  "deal_id": "DL-2026-000001",
  "intake_id": "INT-2026-000001",
  "document_set_id": "DS-2026-000001"
}
```

## 7.6 `BuildTenderSummaryResponse`

```json
{
  "tender_summary_id": "TS-2026-000001",
  "summary_status": "BUILT"
}
```

---

# 8. Minimal structured summary schema

Ниже минимум, который должен существовать уже в Sprint 2A:

```json
{
  "title": "Поставка автоматических выключателей",
  "customer_name": "АО Пример",
  "procurement_number": "123456789",
  "source_type": "MANUAL",
  "document_count": 2,
  "high_level_scope": "Поставка электротехнического оборудования",
  "summary_version": "1.0"
}
```

### Обязательные поля
- `title`
- `customer_name`
- `source_type`
- `document_count`
- `summary_version`

### Опциональные поля
- `procurement_number`
- `high_level_scope`

---

# 9. Event contracts Sprint 2A

## 9.1 Intake events

### `tender_intake_received`
```json
{
  "event_code": "tender_intake_received",
  "deal_id": "DL-2026-000001",
  "payload": {
    "intake_id": "INT-2026-000001",
    "source_type": "MANUAL"
  }
}
```

### `tender_intake_normalized`
### `tender_intake_linked`
### `tender_intake_failed`

---

## 9.2 Document ingestion events

### `document_set_created`
```json
{
  "event_code": "document_set_created",
  "deal_id": "DL-2026-000001",
  "payload": {
    "document_set_id": "DS-2026-000001",
    "item_count": 2
  }
}
```

### `document_ingestion_started`
### `document_ingestion_completed`
### `document_ingestion_partial`
### `document_ingestion_failed`

---

## 9.3 Summary events

### `tender_summary_build_started`
### `tender_summary_built`
### `tender_summary_failed`

---

# 10. Cross-entity relations

## 10.1 Intake-centric graph

```text
deal
 ├─ tender_intake_record [1..N]
 │   └─ tender_source_payload [1..N]
 ├─ document_artifact [0..N]
 ├─ document_set [0..N]
 │   ├─ document_set_item [1..N]
 │   └─ document_ingestion_run [0..N]
 └─ tender_summary [0..N]
     └─ tender_summary_source_link [1..N]
```

---

# 11. Validation rules Sprint 2A

## 11.1 Intake validation
- `source_type` required
- `source_channel` required
- `source_title` required
- `initial_source_type` required
- `direction_type` required
- `domain_type` required
- `payload_json` required

## 11.2 Document set validation
- `deal_id` required
- `intake_id` required
- at least one item recommended
- each `artifact_ref` must exist
- `item_role` required

## 11.3 Summary validation
- referenced `deal_id` must exist
- referenced `intake_id` must exist
- referenced `document_set_id` must exist
- summary must have both text and structured JSON

---

# 12. Migration order Sprint 2A

## Migration 006
- `tender_intake_records`
- `tender_source_payloads`

## Migration 007
- `document_sets`
- `document_set_items`
- `document_ingestion_runs`

## Migration 008
- `tender_summaries`
- `tender_summary_source_links`

---

# 13. Anti-chaos rules for Codex / developer

1. Do not invent another “candidate” entity if `tender_intake_record` already exists.
2. Do not store raw intake payload only inside event log; keep dedicated payload storage.
3. Do not skip `document_set` and jump directly from artifacts to summary.
4. Do not build summary from arbitrary artifact lists without persisted `document_set_id`.
5. Do not bypass M-003 for document references.
6. Do not hide summary source lineage.

---

# 14. What Codex should generate first for Sprint 2A

1. new enums for Sprint 2A
2. ID generators:
   - `INT-*`
   - `DS-*`
   - `DIR-*`
   - `TS-*`
3. migrations 006/007/008
4. ORM models
5. DTOs and validators
6. services:
   - create intake
   - create document set
   - build tender summary
7. event emission hooks
8. integration tests for all main invariants

---

# 15. Acceptance criteria по Entity Catalog Sprint 2A

Каталог готов к кодингу, если:
1. новые entities названы однозначно;
2. refs и formats зафиксированы;
3. enums зафиксированы;
4. graph relations понятны;
5. migration order понятен;
6. Codex не придется придумывать ad hoc intake/document structures самостоятельно.

---

# 16. Итог

Entity Catalog Sprint 2A фиксирует ровно тот слой, который нужен сейчас:
- intake entity,
- document set entity,
- summary entity,
- все IDs, enums, links и invariants.

После этого можно безопасно идти в Codex и кодить Sprint 2A, не рискуя расползанием модели.
