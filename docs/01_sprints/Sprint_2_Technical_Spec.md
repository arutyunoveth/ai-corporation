
# Sprint 2 Technical Spec
## Модули M-008, M-011, M-012

---

## 1. Назначение документа

Этот документ — **техническое ТЗ на Sprint 2A** первой волны разработки.

Sprint 2A строит **intake foundation** поверх уже готового Sprint 1 foundation.

В Sprint 2A реализуются модули:

- **M-008 Tender Intake Pipeline**
- **M-011 Document Ingestion Layer**
- **M-012 Tender Summary Builder**

---

## 2. Результат Sprint 2A

К концу Sprint 2A система должна уметь:

1. принять новый tender candidate из одного из intake channels;
2. создать или обновить `deal` в канонической модели Sprint 1;
3. зарегистрировать intake record;
4. связать raw input и документы с `deal_id`;
5. ingest-ить document set как formal artifacts;
6. зарегистрировать ingestion trace;
7. построить formal tender summary artifact;
8. записать полный audit trail по пути:
   - intake received
   - deal created/updated
   - artifacts linked
   - document set ingested
   - tender summary built

---

## 3. Что НЕ входит в Sprint 2A

В Sprint 2A не реализуются:

- screening decision logic (M-009)
- scoring/prioritization (M-010)
- compliance matrix (M-013)
- document requirements extraction (M-014)
- initial tech risk flags (M-015)
- supplier-side modules
- finance/risk/approval
- submission logic
- owner dashboard

Sprint 2A заканчивается на **formal intake package + summary**.

---

## 4. Зависимости Sprint 2A

Sprint 2A опирается на уже готовые модули Sprint 1:

- M-001 Deal Registry
- M-002 Status Model Engine
- M-003 Document Store
- M-004 Event Log & Decision Journal

И использует существующие foundational concepts:
- `deal_id`
- `artifact_ref`
- `event_id`
- status transition rules
- event append
- artifact storage/linking

---

## 5. Архитектурные принципы Sprint 2A

### Принцип 1. Intake does not bypass Deal Registry
Любой входящий tender candidate должен входить в систему через `deal`.

### Принцип 2. Raw input is not the system object
Сырой portal/email/manual input не является канонической сущностью сделки. Он должен быть преобразован в formal intake record + deal link.

### Принцип 3. Documents must become artifacts
Никаких “файлов просто лежащих рядом”. Только artifacts через M-003.

### Принцип 4. Summary is a formal artifact
Tender summary — это не просто response API, а отдельный persisted output.

### Принцип 5. Audit first
Каждый шаг intake и ingestion должен оставлять formal events.

---

# 6. M-008 — Tender Intake Pipeline

## 6.1 Назначение модуля

`M-008` отвечает за первичный вход закупки в систему.

Он превращает внешний input в:
- canonical deal context;
- intake record;
- linkage to source refs;
- intake events.

---

## 6.2 User stories

### US-201
Как система,  
я хочу принять procurement candidate из external channel,  
чтобы создать formal entry point сделки.

### US-202
Как owner,  
я хочу иметь возможность занести закупку вручную,  
чтобы система не зависела только от автоматических источников.

### US-203
Как downstream analysis modules,  
мы хотим получать deal, который уже связан с source metadata,  
чтобы не разбирать заново исходное происхождение сделки.

---

## 6.3 Основные сущности M-008

### 1. `tender_intake_record`
Каноническая запись о факте входа закупки в систему.

### 2. `tender_source_payload`
Нормализованный raw payload / metadata input.

### 3. `deal_source_binding`
Связь deal с intake record и source metadata.

---

## 6.4 Таблицы M-008

## Таблица `tender_intake_records`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| intake_id | VARCHAR(64) | да | Канонический intake ref, например `INT-2026-000001` |
| deal_id | VARCHAR(32) | да | FK to deals.deal_id |
| source_type | TEXT | да | `PORTAL`, `EMAIL`, `MANUAL`, `API`, `OTHER` |
| source_channel | TEXT | да | Конкретный канал/маршрут intake |
| source_title | TEXT | да | Исходное название закупки |
| source_customer_name | TEXT | да | Заказчик из intake |
| source_procurement_number | TEXT | да | Номер закупки, если есть |
| intake_status | TEXT | да | `RECEIVED`, `NORMALIZED`, `LINKED`, `FAILED` |
| received_at | TIMESTAMP UTC | да | Когда получили input |
| normalized_at | TIMESTAMP UTC | да | Когда превратили в formal intake |
| created_at | TIMESTAMP UTC | да | Дата создания |
| updated_at | TIMESTAMP UTC | да | Дата обновления |

### Индексы
- unique(`intake_id`)
- index(`deal_id`)
- index(`source_type`)
- index(`source_procurement_number`)
- index(`received_at`)

---

## Таблица `tender_source_payloads`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| intake_id | VARCHAR(64) | да | FK to tender_intake_records.intake_id |
| payload_json | JSONB | да | Нормализованный raw input |
| payload_hash | TEXT | да | Хэш полезной нагрузки |
| created_at | TIMESTAMP UTC | да | Дата |

### Индексы
- index(`intake_id`)
- index(`payload_hash`)

---

## 6.5 Intake ID format

### `intake_id`
Формат:
```text
INT-YYYY-NNNNNN
```

Пример:
```text
INT-2026-000001
```

---

## 6.6 Intake statuses

Минимальные значения:
- `RECEIVED`
- `NORMALIZED`
- `LINKED`
- `FAILED`

---

## 6.7 API M-008

### `POST /intake/tenders`
Создать intake record и создать/привязать deal.

#### Request
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

#### Response
```json
{
  "intake_id": "INT-2026-000001",
  "deal_id": "DL-2026-000001",
  "intake_status": "LINKED"
}
```

---

### `GET /intake/tenders/{intake_id}`
Получить intake record.

### `GET /intake/tenders?deal_id=DL-2026-000001`
Получить intake records по сделке.

---

## 6.8 Логика M-008

### Happy path
1. Intake input received.
2. Create `deal` if this is new candidate.
3. Add source refs to deal.
4. Create `tender_intake_record`.
5. Store normalized source payload.
6. Append events:
   - `tender_intake_received`
   - `tender_intake_normalized`
   - `tender_intake_linked`

### Minimal duplicate strategy
На Sprint 2A достаточно soft duplicate check by:
- `source_procurement_number`
- `source_type`
- optional `payload_hash`

Не нужно строить сложный duplicate engine, но нельзя бесконтрольно плодить дубли при одинаковом procurement number без явного сигнала.

---

## 6.9 Acceptance criteria M-008

1. Можно создать `tender_intake_record`.
2. Intake создает или связывает `deal`.
3. Source payload сохраняется отдельно.
4. `intake_id` уникален.
5. Events пишутся в M-004.
6. Intake record searchable by `deal_id` and `intake_id`.

---

# 7. M-011 — Document Ingestion Layer

## 7.1 Назначение модуля

`M-011` превращает набор документов по закупке в formal document ingestion package.

Модуль отвечает не за OCR/глубокий parsing как таковой, а за:
- ingest набора документов;
- регистрацию состава набора;
- привязку artifacts к deal/intake;
- формирование document-set record;
- trace ingestion lifecycle.

---

## 7.2 User stories

### US-204
Как система,  
я хочу intake-ить document set по закупке,  
чтобы downstream modules работали уже с formalized document package.

### US-205
Как owner,  
я хочу видеть, какие документы реально связаны со сделкой,  
чтобы не было хаоса между portal attachments, email files и manual uploads.

### US-206
Как summary/compliance/risk modules,  
мы хотим получать `document_set_id`,  
чтобы downstream analysis шла от formal set, а не от случайных artifact refs.

---

## 7.3 Основные сущности M-011

### 1. `document_set`
Канонический набор документов сделки на этапе intake.

### 2. `document_set_item`
Состав набора документов.

### 3. `document_ingestion_run`
Отдельный запуск ingestion.

---

## 7.4 Таблицы M-011

## Таблица `document_sets`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| document_set_id | VARCHAR(64) | да | Канонический ref, например `DS-2026-000001` |
| deal_id | VARCHAR(32) | да | FK |
| intake_id | VARCHAR(64) | да | FK to intake |
| set_type | TEXT | да | `TENDER_INITIAL`, `TENDER_REFRESH`, `OTHER` |
| ingestion_status | TEXT | да | `CREATED`, `INGESTED`, `PARTIAL`, `FAILED` |
| item_count | INTEGER | да | Кол-во items |
| created_at | TIMESTAMP UTC | да | Дата |
| updated_at | TIMESTAMP UTC | да | Дата |

### Индексы
- unique(`document_set_id`)
- index(`deal_id`)
- index(`intake_id`)
- index(`ingestion_status`)

---

## Таблица `document_set_items`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| document_set_id | VARCHAR(64) | да | FK |
| artifact_ref | VARCHAR(64) | да | FK to document_artifacts.artifact_ref |
| item_role | TEXT | да | `NOTICE`, `TZ`, `DRAFT_CONTRACT`, `ATTACHMENT`, `OTHER` |
| source_file_name | TEXT | да | Исходное имя |
| sort_order | INTEGER | да | Порядок внутри набора |
| created_at | TIMESTAMP UTC | да | Дата |

### Индексы
- index(`document_set_id`)
- index(`artifact_ref`)
- index(`item_role`)

---

## Таблица `document_ingestion_runs`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| ingestion_run_id | VARCHAR(64) | да | Ref, например `DIR-2026-000001` |
| document_set_id | VARCHAR(64) | да | FK |
| run_status | TEXT | да | `STARTED`, `COMPLETED`, `FAILED`, `PARTIAL` |
| started_at | TIMESTAMP UTC | да | Start time |
| finished_at | TIMESTAMP UTC | да | End time |
| notes | TEXT | да | Notes / error summary |

### Индексы
- unique(`ingestion_run_id`)
- index(`document_set_id`)
- index(`run_status`)

---

## 7.5 ID formats

### `document_set_id`
```text
DS-YYYY-NNNNNN
```

### `ingestion_run_id`
```text
DIR-YYYY-NNNNNN
```

---

## 7.6 Ingestion statuses

### document_sets.ingestion_status
- `CREATED`
- `INGESTED`
- `PARTIAL`
- `FAILED`

### document_ingestion_runs.run_status
- `STARTED`
- `COMPLETED`
- `FAILED`
- `PARTIAL`

---

## 7.7 API M-011

### `POST /document-ingestion/sets`
Создать document set и связать artifacts.

#### Request
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
    },
    {
      "artifact_ref": "ART-2026-000002",
      "item_role": "TZ",
      "source_file_name": "specification.pdf",
      "sort_order": 2
    }
  ]
}
```

#### Response
```json
{
  "document_set_id": "DS-2026-000001",
  "ingestion_status": "INGESTED",
  "item_count": 2
}
```

---

### `GET /document-ingestion/sets/{document_set_id}`
### `GET /document-ingestion/sets?deal_id=DL-2026-000001`
### `POST /document-ingestion/sets/{document_set_id}/runs`

---

## 7.8 Логика M-011

### Happy path
1. Intake artifacts already stored in M-003.
2. Create `document_set`.
3. Create `document_set_items`.
4. Create optional `document_ingestion_run`.
5. Mark set `INGESTED`.
6. Write events:
   - `document_set_created`
   - `document_ingestion_started`
   - `document_ingestion_completed`

### Partial path
Если часть artifacts missing or invalid:
- set `PARTIAL`
- run `PARTIAL`
- write `document_ingestion_partial`

---

## 7.9 Acceptance criteria M-011

1. Можно создать formal `document_set`.
2. `document_set` связан и с `deal_id`, и с `intake_id`.
3. Items ссылаются на existing `artifact_ref`.
4. `document_set_id` уникален.
5. Есть ingestion run trace.
6. Events пишутся в M-004.

---

# 8. M-012 — Tender Summary Builder

## 8.1 Назначение модуля

`M-012` строит formal tender summary на основе:
- deal metadata;
- intake metadata;
- document set.

Summary должен быть:
- machine-usable;
- readable для человека;
- persisted as formal artifact/record.

---

## 8.2 User stories

### US-207
Как owner,  
я хочу короткую и полезную summary сделки,  
чтобы быстро понять суть закупки без ручного чтения всей пачки документов.

### US-208
Как downstream modules,  
мы хотим использовать summary как reusable artifact,  
чтобы screening and scoring не строили все с нуля.

### US-209
Как audit/governance layer,  
мы хотим знать, какая summary была построена и на основе какого document set.

---

## 8.3 Основные сущности M-012

### 1. `tender_summary_record`
Канонический summary object.

### 2. `tender_summary_source_link`
Связь summary с deal/intake/document set/artifact.

### 3. `tender_summary_artifact_binding`
Связь summary с artifact ref, если summary сохраняется и как artifact.

---

## 8.4 Таблицы M-012

## Таблица `tender_summaries`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| tender_summary_id | VARCHAR(64) | да | Ref, например `TS-2026-000001` |
| deal_id | VARCHAR(32) | да | FK |
| intake_id | VARCHAR(64) | да | FK |
| document_set_id | VARCHAR(64) | да | FK |
| summary_status | TEXT | да | `BUILT`, `FAILED`, `STALE` |
| summary_text | TEXT | да | Человеко-читаемый summary |
| structured_summary_json | JSONB | да | Structured output |
| created_at | TIMESTAMP UTC | да | Дата |
| updated_at | TIMESTAMP UTC | да | Дата |

### Индексы
- unique(`tender_summary_id`)
- index(`deal_id`)
- index(`intake_id`)
- index(`document_set_id`)
- index(`summary_status`)

---

## Таблица `tender_summary_source_links`

| Поле | Тип | Обяз. | Описание |
|---|---|---:|---|
| id | UUID / BIGINT | да | PK |
| tender_summary_id | VARCHAR(64) | да | FK |
| source_object_type | TEXT | да | `DEAL`, `INTAKE`, `DOCUMENT_SET`, `ARTIFACT` |
| source_object_ref | TEXT | да | Ref объекта |
| created_at | TIMESTAMP UTC | да | Дата |

### Индексы
- index(`tender_summary_id`)
- index(`source_object_type`, `source_object_ref`)

---

## 8.5 ID format

### `tender_summary_id`
```text
TS-YYYY-NNNNNN
```

---

## 8.6 Summary statuses

- `BUILT`
- `FAILED`
- `STALE`

---

## 8.7 Structured summary minimum schema

Минимальный JSON:
```json
{
  "title": "Поставка автоматических выключателей",
  "customer_name": "АО Пример",
  "procurement_number": "123456789",
  "document_count": 2,
  "source_type": "MANUAL",
  "high_level_scope": "Поставка электротехнического оборудования",
  "summary_version": "1.0"
}
```

На Sprint 2A summary может быть простым и rule-based.  
Не нужно строить сложный LLM pipeline, если foundation еще формируется.

---

## 8.8 API M-012

### `POST /tender-summaries`
Построить summary.

#### Request
```json
{
  "deal_id": "DL-2026-000001",
  "intake_id": "INT-2026-000001",
  "document_set_id": "DS-2026-000001"
}
```

#### Response
```json
{
  "tender_summary_id": "TS-2026-000001",
  "summary_status": "BUILT"
}
```

---

### `GET /tender-summaries/{tender_summary_id}`
### `GET /tender-summaries?deal_id=DL-2026-000001`

---

## 8.9 Логика M-012

### Happy path
1. Load deal.
2. Load intake.
3. Load document set.
4. Build structured summary JSON.
5. Build readable summary text.
6. Persist `tender_summary_record`.
7. Create source links.
8. Write events:
   - `tender_summary_build_started`
   - `tender_summary_built`

### Stale path
Если в будущем document set updated:
- existing summary may be marked `STALE`.

В Sprint 2A достаточно:
- поддержать поле и статус,
- не строить full stale recalculation engine.

---

## 8.10 Acceptance criteria M-012

1. Можно построить summary по `deal_id + intake_id + document_set_id`.
2. Summary сохраняется как formal record.
3. Есть `summary_text` и `structured_summary_json`.
4. Есть source links.
5. Events пишутся в M-004.
6. Summary can be queried by deal.

---

# 9. Общие события Sprint 2A

Минимальный event dictionary:

- `tender_intake_received`
- `tender_intake_normalized`
- `tender_intake_linked`
- `tender_intake_failed`

- `document_set_created`
- `document_ingestion_started`
- `document_ingestion_completed`
- `document_ingestion_partial`
- `document_ingestion_failed`

- `tender_summary_build_started`
- `tender_summary_built`
- `tender_summary_failed`

---

# 10. Общие enums Sprint 2A

## 10.1 `TenderSourceType`
```text
PORTAL
EMAIL
MANUAL
API
OTHER
```

## 10.2 `IntakeStatus`
```text
RECEIVED
NORMALIZED
LINKED
FAILED
```

## 10.3 `DocumentSetType`
```text
TENDER_INITIAL
TENDER_REFRESH
OTHER
```

## 10.4 `DocumentIngestionStatus`
```text
CREATED
INGESTED
PARTIAL
FAILED
```

## 10.5 `DocumentIngestionRunStatus`
```text
STARTED
COMPLETED
FAILED
PARTIAL
```

## 10.6 `DocumentSetItemRole`
```text
NOTICE
TZ
DRAFT_CONTRACT
ATTACHMENT
OTHER
```

## 10.7 `TenderSummaryStatus`
```text
BUILT
FAILED
STALE
```

---

# 11. Межмодульные связи Sprint 2A

## 11.1 Поток данных

```text
raw tender input
  -> M-008 tender_intake_record + deal
  -> M-003 artifacts
  -> M-011 document_set
  -> M-012 tender_summary
```

## 11.2 Deal-centric graph after Sprint 2A

```text
deal
 ├─ tender_intake_record [1..N]
 ├─ document_artifact [0..N]
 ├─ document_set [0..N]
 ├─ tender_summary [0..N]
 ├─ event_record [0..N]
 └─ decision_record [0..N]
```

---

# 12. API set Sprint 2A

Обязательные endpoints:

## Intake
- `POST /intake/tenders`
- `GET /intake/tenders/{intake_id}`
- `GET /intake/tenders?deal_id=...`

## Document ingestion
- `POST /document-ingestion/sets`
- `GET /document-ingestion/sets/{document_set_id}`
- `GET /document-ingestion/sets?deal_id=...`
- `POST /document-ingestion/sets/{document_set_id}/runs`

## Summary
- `POST /tender-summaries`
- `GET /tender-summaries/{tender_summary_id}`
- `GET /tender-summaries?deal_id=...`

---

# 13. Migration order Sprint 2A

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

# 14. Acceptance criteria по всему Sprint 2A

Sprint 2A завершен, если:

1. можно создать intake record;
2. intake привязан к canonical deal;
3. source payload preserved;
4. можно собрать document set из existing artifacts;
5. можно связать document set с intake и deal;
6. можно построить formal tender summary;
7. summary queryable by deal;
8. все этапы оставляют audit events;
9. foundation совместима с будущими M-009, M-010, M-013, M-014, M-015.

---

# 15. Что делать сразу после Sprint 2A

После Sprint 2A логичный следующий шаг — **Sprint 2B**:

- M-009 Tender Screening Engine
- M-010 Priority Scoring Engine
- M-013 Compliance Matrix Builder
- M-014 Document Requirement Extractor
- M-015 Initial Tech Risk Flags

Но переходить туда стоит только после того, как:
- intake record стабилен,
- document set model стабилен,
- summary record стабилен,
- не требуется пересобирать entity model Sprint 2A.

---

# 16. Итог

Sprint 2A — это модульный мост между foundation и реальной аналитикой закупки.

Если он сделан правильно:
- downstream-модули начнут работать не с сырьем, а с formal intake package;
- supplier-side и analysis не придется строить на хаосе;
- Codex не начнет придумывать собственные ad hoc сущности для intake and document flow.
