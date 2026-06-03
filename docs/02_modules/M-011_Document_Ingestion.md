# Карточка модуля M-011 — Документ-инжест

## 1. Общая информация

- **ID модуля:** M-011
- **Название:** Документ-инжест
- **Приоритет:** P0
- **Спринт:** 3
- **Тип модуля:** Document Intake / Deep Work Entry / Procurement Document Capture
- **Статус:** Draft
- **Связанные документы:**
  - M-001 Deal Card Core
  - M-002 Статусная модель сделки
  - M-003 Хранилище документов
  - M-004 Журнал событий и решений
  - M-007 Импорт закупок из источников
  - M-008 Нормализация закупки
  - M-010 Intake Summary / Prioritization
  - M-012 Извлечение требований из ТЗ
  - M-013 Compliance Matrix Builder
  - M-014 Document Requirement Extractor
  - M-051 Workflow Orchestrator
  - оргструктура компании
  - сквозной жизненный цикл сделки
  - реестр модулей системы
  - таблица этапов сделки

---

## 2. Назначение модуля

Модуль `M-011` отвечает за intake и формальную регистрацию документов закупки перед глубокой проработкой.

Если:
- `M-010` определил, что candidate нужно брать в глубокий анализ,
- `M-003` уже задает каноническое хранилище документов,

то `M-011` отвечает на вопрос:

**"Как собрать, привязать, классифицировать и завести в систему весь комплект документов конкретной закупки так, чтобы downstream-модули могли работать по ним формально и воспроизводимо?"**

### Главный принцип
**Нельзя переходить к deep analysis без формального document ingestion: все ключевые документы закупки должны быть заведены, классифицированы и связаны с Deal Card.**

---

## 3. Роль модуля в системе

Документ-инжест нужен для 10 целей:

1. **Собрать документы закупки из доступных источников**
2. **Подтянуть документы по ссылкам из normalized payload / portal**
3. **Зарегистрировать документы в M-003**
4. **Привязать документы к сделке**
5. **Классифицировать первичный набор документов**
6. **Определить полноту документного комплекта**
7. **Понять, есть ли ТЗ, проект договора, формы заявки, разъяснения**
8. **Подготовить downstream-доступ для ТЗ-анализа**
9. **Создать summary документного комплекта**
10. **Перевести сделку в реальную стадию document-driven analysis**

---

## 4. Цель модуля

Создать document intake layer, который:

1. получает candidate deal;
2. извлекает список доступных документных источников;
3. скачивает или принимает документы;
4. регистрирует их в M-003;
5. определяет базовые document types;
6. формирует document set summary;
7. показывает, чего не хватает;
8. подготавливает сделку к M-012 / M-014 / M-026;
9. эмитит событие `document_set_ingested`.

---

## 5. Границы ответственности модуля

### Модуль отвечает за:
- сбор и intake документов закупки;
- скачивание документов по ссылкам;
- регистрацию документов через M-003;
- привязку документов к Deal Card;
- первичную классификацию набора;
- проверку наличия ключевых document classes;
- формирование procurement document set summary;
- оценку document completeness.

### Модуль не отвечает за:
- глубокий парсинг ТЗ;
- извлечение требований;
- построение compliance matrix;
- извлечение обязательных документов заявки;
- договорной анализ;
- решение, участвовать или нет.

---

## 6. Этапы сделки, на которых работает модуль

Основной этап:
- **после candidate prioritization, перед deep analysis**

Основные статусы:
- вход: `CANDIDATE`
- downstream: подготовка к `DOCS_ANALYSIS`

Обычно именно этот модуль становится первой реальной операцией на пути к `DOCS_ANALYSIS`.

---

## 7. User story

### Бизнес user story
Как владелец компании,  
я хочу, чтобы после выбора candidate система сама собрала и завела весь комплект документов закупки,  
чтобы deep analysis начинался на полном и формальном наборе файлов, а не на случайной ссылке или одном PDF.

### Техническая user story
Как document-intake layer,  
я хочу получить candidate deal и привести все доступные документы закупки в каноническое document store,  
чтобы downstream-модули могли читать документы по `document_id`, а не по сырым ссылкам.

---

## 8. Входы модуля

### Основные входы
- Deal Card summary
- normalized payload from M-008
- intake summary from M-010
- document links из normalized payload
- source portal / tender page references
- manual document upload fallback

### Типовые входные события
- `candidate_prioritized`
- `document_ingestion_requested`
- `candidate_selected_for_deep_analysis`
- `document_set_refresh_requested`

### Минимальный payload
```json
{
  "deal_id": "DL-2026-000001",
  "intake_summary_id": "IS-2026-000001",
  "normalization_id": "NM-2026-000001",
  "source_type": "EIS",
  "source_url": "https://example.com/tender/223-ABC-001",
  "document_links": [
    "https://example.com/docs/notice.pdf",
    "https://example.com/docs/tech_spec.pdf",
    "https://example.com/docs/project_contract.pdf"
  ]
}
```

---

## 9. Выходы модуля

### Основной output
Procurement Document Set Summary.

### Побочные output
- зарегистрированные document records в M-003;
- список document_ids;
- document type coverage;
- missing document classes;
- событие `document_set_ingested`;
- readiness signal для M-012 / M-014 / M-026.

---

## 10. Каноническая модель procurement document set summary

## 10.1 Верхний уровень

```json
{
  "document_set_id": "DS-2026-000001",
  "deal_id": "DL-2026-000001",
  "created_at": "2026-06-02T10:00:00Z",
  "document_set_summary": {},
  "coverage": {},
  "missing_items": [],
  "audit": {}
}
```

---

## 10.2 Блок `document_set_summary`

```json
{
  "document_ids": [
    "DOC-2026-000010",
    "DOC-2026-000011",
    "DOC-2026-000012"
  ],
  "document_count": 3,
  "has_notice": true,
  "has_tech_spec": true,
  "has_project_contract": true,
  "has_procurement_forms": false,
  "has_clarifications": false,
  "ingestion_mode": "AUTO|MANUAL|MIXED"
}
```

---

## 10.3 Блок `coverage`

```json
{
  "coverage_score": 0.72,
  "required_document_classes_found": [
    "NOTICE",
    "TECH_SPEC",
    "PROJECT_CONTRACT"
  ],
  "required_document_classes_missing": [
    "PROCUREMENT_FORM"
  ],
  "requires_manual_document_followup": true
}
```

---

## 10.4 Блок `missing_items`

```json
[
  {
    "document_class": "PROCUREMENT_FORM",
    "severity": "WARNING",
    "message": "Procurement forms were not found during document intake"
  }
]
```

---

## 10.5 Блок `audit`

```json
{
  "created_by_module": "M-011",
  "created_at": "2026-06-02T10:00:00Z",
  "ingestion_strategy": "SOURCE_LINKS_PLUS_PORTAL_DISCOVERY",
  "document_ingestion_version": "1.0.0"
}
```

---

## 11. Ключевые document classes для deep analysis

На старте модуль должен пытаться найти и классифицировать как минимум:

- `NOTICE`
- `TECH_SPEC`
- `PROJECT_CONTRACT`
- `PROCUREMENT_FORM`
- `CLARIFICATION`

### Дополнительно, если доступны
- `SUPPORTING_ATTACHMENT`
- `CUSTOMER_REQUIREMENT_APPENDIX`
- `BID_TEMPLATE`
- `FAQ_OR_EXPLANATION_DOC`

---

## 12. Бизнес-правила

### Правило 1
До deep analysis документы должны быть заведены через M-003, а не читаться напрямую по внешним URL.

### Правило 2
Если документный комплект неполный, это должно быть явно отражено в coverage.

### Правило 3
Отсутствие части документов не должно ломать pipeline целиком, если deep analysis по доступным документам все равно имеет смысл.

### Правило 4
Если ключевой документ отсутствует, это должно создавать warning или manual followup.

### Правило 5
Один и тот же документ не должен регистрироваться повторно без проверки дубликатов/checksum.

### Правило 6
Если документ уже есть в M-003 как current version для этой сделки, надо использовать существующую запись, а не плодить копии.

### Правило 7
Document intake должен поддерживать refresh, потому что на поздних стадиях могут появляться новые разъяснения и редакции.

---

## 13. Полнота документного комплекта

Модуль должен считать как минимум:

### `coverage_score`
Насколько полно собран документный комплект для перехода к deep analysis.

### `requires_manual_document_followup`
Флаг, если:
- нет ТЗ;
- нет проекта договора;
- отсутствуют формы/критичные приложения;
- не удалось скачать документы.

### Минимально достаточный комплект для запуска deep analysis
Обычно:
- ТЗ или эквивалент спецификации
- извещение или summary закупки
- проект договора, если он есть в закупке

---

## 14. Связи с другими модулями

### Модуль потребляется:
- M-012 Извлечение требований из ТЗ
- M-014 Document Requirement Extractor
- M-026 Contract Risk Parser
- M-051 Workflow Orchestrator
- M-054 Master Dashboard

### Модуль зависит от:
- M-003 Хранилище документов
- M-008 Нормализация закупки
- M-010 Intake Summary / Prioritization
- document download adapters
- source portal discovery rules

---

## 15. API / операции модуля

### 15.1 Ingest Document Set
Собирает документный комплект закупки.

### 15.2 Register Discovered Documents
Регистрирует найденные документы через M-003.

### 15.3 Build Document Set Summary
Создает summary по комплекту документов.

### 15.4 Refresh Document Set
Повторно выполняет document intake.

### 15.5 Get Document Set Summary
Возвращает summary по комплекту.

### 15.6 Emit Document Set Ingested
Создает событие `document_set_ingested`.

---

## 16. Пример API-операций

## 16.1 Ingest
```json
{
  "operation": "ingest_document_set",
  "payload": {
    "deal_id": "DL-2026-000001",
    "intake_summary_id": "IS-2026-000001",
    "source_type": "EIS",
    "source_url": "https://example.com/tender/223-ABC-001",
    "document_links": [
      "https://example.com/docs/notice.pdf",
      "https://example.com/docs/tech_spec.pdf",
      "https://example.com/docs/project_contract.pdf"
    ]
  }
}
```

## 16.2 Response
```json
{
  "document_set_id": "DS-2026-000001",
  "deal_id": "DL-2026-000001",
  "coverage_score": 0.72,
  "requires_manual_document_followup": true
}
```

## 16.3 Refresh
```json
{
  "operation": "refresh_document_set",
  "payload": {
    "deal_id": "DL-2026-000001",
    "document_set_id": "DS-2026-000001",
    "reason": "New clarification documents expected"
  }
}
```

---

## 17. Workflow-логика модуля

### Сценарий 1. Стандартный document intake
1. M-010 ставит candidate в верхнюю часть очереди.
2. Orchestrator запускает M-011.
3. M-011 берет document links и/или source page.
4. Загружает найденные документы.
5. Регистрирует их в M-003.
6. Привязывает document_ids к Deal Card.
7. Строит document set summary.
8. Эмитит `document_set_ingested`.
9. Передает сигнал на M-012/M-014/M-026.

### Сценарий 2. Неполный комплект
1. Документов найдено мало.
2. M-011 все равно регистрирует то, что есть.
3. В summary отмечает missing classes.
4. Выставляет `requires_manual_document_followup = true`.
5. Downstream может продолжить с warning или ждать refresh.

### Сценарий 3. Refresh / update
1. Появились разъяснения или новые приложения.
2. Запускается refresh.
3. Новые документы инжестятся и регистрируются.
4. Summary обновляется.
5. История старых записей не теряется.

---

## 18. Red flags и exceptions

### Red flags
- document link не скачивается;
- найденные файлы пустые или поврежденные;
- ТЗ отсутствует;
- проект договора отсутствует, хотя должен быть;
- документы есть, но не удается классифицировать;
- документы дублируются по checksum;
- source page ссылается на невалидные или закрытые файлы.

### Exceptions
- закупка содержит только одну общую PDF-книгу со всеми приложениями;
- документы доступны только вручную;
- часть документов появляется позже;
- source page скрывает ссылки за JS/динамикой;
- customer portal требует дополнительную аутентификацию.

### Как обрабатывать
- регистрировать partial success;
- не ломать комплект из-за одного нескачанного файла;
- фиксировать missing classes;
- писать download/classification warnings;
- разрешать manual followup.

---

## 19. UI-требования

### В MVP нужен document intake monitor
Показывать:
- deal_id;
- source_type;
- document_set_id;
- document_count;
- coverage_score;
- required document classes found/missing;
- requires_manual_document_followup;
- last refresh time.

### Drill-down
- список document_ids;
- missing items;
- download failures;
- refresh action;
- open document store records.

---

## 20. Требования к аудиту

Модуль должен писать в M-004:
- `document_intake_started`
- `document_download_succeeded`
- `document_download_failed`
- `document_registered`
- `document_set_ingested`
- `document_set_refreshed`
- `document_set_missing_required_class`

Также нужно хранить:
- document ingestion run id;
- source document URLs;
- download result by file;
- whether file came from auto or manual channel.

---

## 21. Требования к данным

### Таблица / сущность `procurement_document_sets`
Обязательные поля:
- `document_set_id`
- `deal_id`
- `document_count`
- `coverage_score`
- `requires_manual_document_followup`
- `created_at`
- `updated_at`

### Таблица / сущность `document_set_items`
- `document_set_id`
- `document_id`
- `document_class`
- `is_required`
- `is_found`
- `source_url`
- `ingestion_result`

### Таблица / сущность `document_ingestion_runs`
- `document_ingestion_run_id`
- `deal_id`
- `started_at`
- `finished_at`
- `documents_attempted`
- `documents_registered`
- `failures_count`
- `run_status`

---

## 22. Definition of Done

Модуль считается готовым, если:

1. Система умеет запускать document intake для candidate deal.  
2. Найденные документы регистрируются в M-003.  
3. Deal Card получает ссылки на document records.  
4. Строится procurement document set summary.  
5. Считается coverage score.  
6. Missing document classes фиксируются явно.  
7. Есть поддержка partial success.  
8. Есть refresh document set.  
9. Есть document intake monitor UI.  
10. M-011 реально открывает дорогу к deep analysis модулям.

---

## 23. Тест-кейсы

### Позитивные
1. Инжест notice + tech spec + project contract
2. Partial intake без procurement forms
3. Регистрация документов через M-003
4. Обновление document set после refresh
5. Deal Card получает document links
6. Coverage score считается корректно
7. Downstream получает `document_set_ingested`

### Негативные
8. Не скачивается один из документов
9. ТЗ отсутствует
10. Один и тот же документ регистрируется дублем
11. Документ скачан, но не привязан к deal
12. Summary показывает coverage без missing classes
13. Refresh затирает историю старого document set

---

## 24. ТЗ для Codex / разработчика

### Задача
Реализовать модуль `M-011 Документ-инжест` как слой сбора и формального заведения комплектов документов закупки перед deep analysis.

### Нужно сделать
1. Спроектировать schema procurement document set.
2. Реализовать document download / intake adapters.
3. Реализовать регистрацию документов через M-003.
4. Реализовать document set summary.
5. Реализовать coverage score.
6. Реализовать missing document class tracking.
7. Реализовать refresh document set.
8. Реализовать partial success processing.
9. Реализовать document intake monitor UI.
10. Реализовать интеграцию с M-003, M-010, M-012, M-014, M-026 и M-051.

### Ограничения
- нельзя читать deep analysis документы напрямую по URL без M-003;
- нельзя терять историю refresh/update;
- нельзя ломать весь intake из-за одного failed file;
- нельзя считать document set complete без явной проверки required classes;
- нельзя плодить duplicate document records без checksum/dedup проверки.

### Рекомендация по реализации
Подходит схема:
- таблица `procurement_document_sets`
- таблица `document_set_items`
- таблица `document_ingestion_runs`
- download adapters
- portal discovery layer
- M-003 integration service
- coverage calculator
- refresh workflow

Для MVP сначала поддержать:
- document links from normalized payload
- source page discovery
- manual file fallback

---

## 25. Следующий модуль после завершения

После завершения `M-011` логически идет:
- **M-012 Извлечение требований из ТЗ**

Почему:
как только комплект документов формально собран и зарегистрирован, следующий шаг — начать извлекать из ТЗ и приложений реальные требования, на которых потом строятся compliance matrix, supplier fit и вся дальнейшая логика сделки.
