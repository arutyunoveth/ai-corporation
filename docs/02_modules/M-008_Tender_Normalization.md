# Карточка модуля M-008 — Нормализация закупки

## 1. Общая информация

- **ID модуля:** M-008
- **Название:** Нормализация закупки
- **Приоритет:** P0
- **Спринт:** 2
- **Тип модуля:** Intake Processing / Data Normalization Layer
- **Статус:** Draft
- **Связанные документы:**
  - M-001 Deal Card Core
  - M-002 Статусная модель сделки
  - M-003 Хранилище документов
  - M-004 Журнал событий и решений
  - M-007 Импорт закупок из источников
  - M-009 Screening Engine
  - M-051 Workflow Orchestrator
  - M-054 Master Dashboard
  - оргструктура компании
  - сквозной жизненный цикл сделки
  - реестр модулей системы
  - таблица этапов сделки

---

## 2. Назначение модуля

Модуль `M-008` отвечает за преобразование сырого intake-потока в единый стандартизированный payload закупки.

Если `M-007` отвечает на вопрос  
**"как сигнал о закупке попал в систему?"**,  
то `M-008` отвечает на вопрос:

**"как привести разные, неполные и разноформатные входящие записи к единой модели, на которой дальше сможет работать вся компания?"**

### Главный принцип
**Ни один downstream-модуль не должен работать напрямую с сырым payload источника, если он не прошел стадию нормализации.**

---

## 3. Роль модуля в системе

Нормализация закупки нужна для 10 целей:

1. **Унификация разных источников**
2. **Приведение полей к единому контракту**
3. **Выделение минимально полезных бизнес-атрибутов**
4. **Нормализация дат, сумм, валют, названий**
5. **Заполнение канонической source-модели**
6. **Подготовка payload для создания/обновления Deal Card**
7. **Подготовка данных для screening**
8. **Маркировка полноты и качества входящих данных**
9. **Выделение отсутствующих и сомнительных полей**
10. **Снижение зависимости downstream от особенностей конкретного источника**

---

## 4. Цель модуля

Создать normalization layer, который:

1. принимает raw intake record;
2. извлекает ключевые поля из разных source payload;
3. приводит поля к каноническому формату;
4. оценивает completeness и confidence;
5. формирует normalized tender payload;
6. указывает missing / ambiguous fields;
7. подготавливает данные для M-001 и M-009;
8. публикует событие `tender_normalized`.

---

## 5. Границы ответственности модуля

### Модуль отвечает за:
- чтение raw intake record;
- source-specific field mapping;
- канонизацию названия закупки;
- нормализацию сроков;
- нормализацию суммы и валюты;
- нормализацию имени заказчика;
- нормализацию procurement model candidate;
- определение наличия документов;
- выставление completeness score;
- формирование normalized payload.

### Модуль не отвечает за:
- оценку fit сделки;
- go/no-go screening;
- глубокий анализ ТЗ;
- supplier sourcing;
- расчет экономики;
- статусный переход beyond NEW_SIGNAL/SCREENING logic;
- human approval.

Это следующий контур:
- M-009 Screening Engine
- и далее.

---

## 6. Этапы сделки, на которых работает модуль

Основной этап:
- **Этап 0–1: входящий сигнал → подготовка к screening**

Основной downstream-статус:
- `NEW_SIGNAL`
- затем передача в `SCREENING`

---

## 7. User story

### Бизнес user story
Как владелец компании,  
я хочу, чтобы закупки из разных источников приводились к единому виду до screening,  
чтобы downstream-решения принимались на стабильных и сопоставимых данных.

### Техническая user story
Как intake-processing layer,  
я хочу получать raw intake records и превращать их в standardized normalized payload,  
чтобы Deal Card и Screening Engine не знали ничего о различиях между EIS, частным порталом, email и manual input.

---

## 8. Входы модуля

### Источники входа
- M-007 intake records
- manual reprocess requests
- normalization retry
- source-specific parser outputs

### Типовые входные события
- `new_tender_detected`
- `intake_reprocess_requested`
- `source_mapping_updated`

### Минимальный payload
```json
{
  "intake_record_id": "IN-2026-000001",
  "deal_candidate_external_id": "223-ABC-001",
  "source_type": "EIS",
  "raw_payload_uri": "storage://intake/raw/IN-2026-000001.json",
  "raw_title": "Поставка электротехнического оборудования"
}
```

---

## 9. Выходы модуля

### Основной output
Normalized Tender Payload.

### Побочные output
- normalization record;
- completeness score;
- field-level warnings;
- missing fields list;
- событие `tender_normalized`;
- payload для M-001 Deal Card Core;
- payload для M-009 Screening Engine.

---

## 10. Каноническая модель normalized tender payload

## 10.1 Верхний уровень

```json
{
  "normalization_id": "NM-2026-000001",
  "intake_record_id": "IN-2026-000001",
  "source_type": "EIS",
  "normalized_at": "2026-06-02T10:00:00Z",
  "normalized_payload": {},
  "quality": {},
  "field_warnings": [],
  "audit": {}
}
```

---

## 10.2 Блок `normalized_payload`

```json
{
  "external_id": "223-ABC-001",
  "source_url": "https://example.com/tender/223-ABC-001",
  "title": "Поставка электротехнического оборудования",
  "customer_name": "ООО Промышленный заказчик",
  "customer_inn": null,
  "procurement_model_candidate": "223_FZ",
  "procedure_type": "open_request",
  "published_at": "2026-06-02T09:00:00Z",
  "deadline_at": "2026-06-05T18:00:00Z",
  "budget_amount": 12500000,
  "currency": "RUB",
  "region": null,
  "delivery_place": null,
  "delivery_deadline": null,
  "documents_available": true,
  "document_links": [],
  "raw_source_confidence": 0.94
}
```

---

## 10.3 Блок `quality`

```json
{
  "completeness_score": 0.82,
  "normalization_confidence": 0.93,
  "missing_fields": ["customer_inn", "delivery_place"],
  "ambiguous_fields": [],
  "requires_manual_review": false
}
```

---

## 10.4 Блок `field_warnings`

```json
[
  {
    "field": "procurement_model_candidate",
    "warning_code": "INFERRED_FROM_SOURCE_TYPE",
    "severity": "INFO",
    "message": "Procurement model was inferred from source type"
  }
]
```

---

## 10.5 Блок `audit`

```json
{
  "created_by_module": "M-008",
  "created_at": "2026-06-02T10:00:00Z",
  "source_mapping_version": "1.0.0",
  "normalization_strategy": "SOURCE_MAPPING_PLUS_RULES"
}
```

---

## 11. Канонический набор нормализуемых полей

Минимальный обязательный normalized contract для downstream:

- `external_id`
- `source_url`
- `title`
- `customer_name`
- `procurement_model_candidate`
- `published_at`
- `deadline_at`
- `budget_amount`
- `currency`
- `documents_available`

### Расширяемые поля
- `customer_inn`
- `procedure_type`
- `region`
- `delivery_place`
- `delivery_deadline`
- `document_links`
- `category_guess`
- `platform_name`

---

## 12. Бизнес-правила

### Правило 1
Нормализация не должна уничтожать raw trace.  
Raw payload всегда остается доступен через intake record.

### Правило 2
Если поле невозможно извлечь надежно, оно должно быть:
- либо `null`,
- либо вынесено в `ambiguous_fields`,
а не выдумано.

### Правило 3
Inference должен быть явно помечен в `field_warnings`.

### Правило 4
Normalized payload должен быть стабильным независимо от source format.

### Правило 5
Downstream-модули должны читать normalized payload, а не source-specific raw.

### Правило 6
Если completeness слишком низкий, нужно ставить флаг `requires_manual_review = true` или отдавать на осторожный screening.

### Правило 7
Нормализация должна быть идемпотентной для одной и той же версии intake record.

---

## 13. Качество нормализации

Модуль должен рассчитывать как минимум:

### `completeness_score`
Доля заполненных полезных полей для downstream.

### `normalization_confidence`
Насколько система уверена, что mapping корректен.

### `requires_manual_review`
Флаг, если:
- слишком много missing fields;
- слишком много ambiguous fields;
- конфликтуют значения полей;
- дата / сумма / заказчик выглядят ненадежно.

---

## 14. Связи с другими модулями

### Модуль потребляется:
- M-001 Deal Card Core
- M-009 Screening Engine
- M-004 Event Log
- M-051 Workflow Orchestrator
- M-054 Master Dashboard

### Модуль зависит от:
- M-007 Импорт закупок из источников
- source-specific mapping rules
- storage для raw payload
- M-004 для логирования
- M-001 downstream для создания/обновления Deal Card

---

## 15. API / операции модуля

### 15.1 Normalize Intake Record
Нормализует intake record в канонический payload.

### 15.2 Get Normalized Payload
Возвращает результат нормализации.

### 15.3 Re-Normalize
Повторно выполняет нормализацию после изменения mapping rules.

### 15.4 Validate Normalized Payload
Проверяет полноту и корректность normalized contract.

### 15.5 Emit Tender Normalized Event
Создает событие `tender_normalized`.

---

## 16. Пример API-операций

## 16.1 Normalize
```json
{
  "operation": "normalize_intake_record",
  "payload": {
    "intake_record_id": "IN-2026-000001",
    "source_type": "EIS",
    "raw_payload_uri": "storage://intake/raw/IN-2026-000001.json"
  }
}
```

## 16.2 Response
```json
{
  "normalization_id": "NM-2026-000001",
  "intake_record_id": "IN-2026-000001",
  "normalized_payload_ref": "normalized://NM-2026-000001",
  "completeness_score": 0.82,
  "requires_manual_review": false
}
```

## 16.3 Emit Event
```json
{
  "operation": "emit_tender_normalized_event",
  "payload": {
    "normalization_id": "NM-2026-000001",
    "intake_record_id": "IN-2026-000001",
    "deal_candidate_external_id": "223-ABC-001"
  }
}
```

---

## 17. Workflow-логика модуля

### Сценарий 1. Нормальный intake path
1. M-007 создает `new_tender_detected`.
2. Orchestrator передает intake record в M-008.
3. M-008 читает raw payload.
4. Применяет source mapping rules.
5. Строит normalized payload.
6. Считает completeness/confidence.
7. Пишет normalization record.
8. Эмитит `tender_normalized`.
9. Передает normalized payload в M-001 / M-009.

### Сценарий 2. Неполные данные
1. Raw payload содержит неполную запись.
2. M-008 заполняет доступные поля.
3. Отсутствующие поля явно помечаются.
4. Если порог completeness ниже нормы — ставится `requires_manual_review`.
5. Downstream может принять осторожное решение или вернуть в review.

### Сценарий 3. Re-normalization
1. Изменились mapping rules.
2. Intake record отправляют на повторную нормализацию.
3. Создается новая normalization record version.
4. История прошлой версии сохраняется.

---

## 18. Red flags и exceptions

### Red flags
- raw payload недоступен;
- поле title пустое после нормализации;
- срок подачи не распарсился;
- сумма распарсилась некорректно;
- procurement model candidate конфликтует с source type;
- documents_available=true, но ссылок на документы нет;
- completeness слишком низкий для reliable screening.

### Exceptions
- источник дает только заголовок и ссылку;
- даты в нестандартном формате;
- бюджет указан текстом;
- заказчик не указан явно;
- procurement model нужно выводить косвенно.

### Как обрабатывать
- сохранять normalized payload даже если неполный;
- помечать warnings;
- не выдумывать отсутствующие поля;
- выставлять `requires_manual_review`;
- логировать normalization anomaly event.

---

## 19. UI-требования

### В MVP нужен normalization monitor
Показывать:
- intake_record_id;
- source_type;
- title;
- completeness_score;
- normalization_confidence;
- requires_manual_review;
- missing fields count;
- ambiguous fields count;
- linked Deal Card, если уже создана.

### Drill-down
- raw intake payload;
- normalized payload;
- field warnings;
- re-normalize action.

---

## 20. Требования к аудиту

Модуль должен писать в M-004:
- `tender_normalization_started`
- `tender_normalized`
- `tender_normalization_warning`
- `tender_normalization_failed`
- `tender_renormalized`

Также нужно хранить:
- source mapping version;
- normalization strategy;
- previous normalization refs;
- who/what triggered re-normalization.

---

## 21. Требования к данным

### Таблица / сущность `normalized_tender_records`
Обязательные поля:
- `normalization_id`
- `intake_record_id`
- `source_type`
- `normalized_payload_json`
- `completeness_score`
- `normalization_confidence`
- `requires_manual_review`
- `created_at`
- `source_mapping_version`

### Таблица / сущность `normalization_field_warnings`
- `normalization_id`
- `field_name`
- `warning_code`
- `severity`
- `message`

### Таблица / сущность `normalization_versions`
- `normalization_id`
- `previous_normalization_id`
- `version`
- `trigger_reason`

---

## 22. Definition of Done

Модуль считается готовым, если:

1. Система умеет взять raw intake record и построить normalized payload.  
2. Нормализованный payload имеет канонический формат.  
3. Поля даты, суммы, валюты и заголовка приводятся к стабильному виду.  
4. Есть completeness_score и normalization_confidence.  
5. Missing / ambiguous fields фиксируются явно.  
6. Есть флаг requires_manual_review.  
7. Создается событие `tender_normalized`.  
8. M-001 и M-009 могут потреблять normalized payload без знания source-specific структуры.  
9. Есть монитор нормализации.  
10. Поддерживается re-normalization без потери истории.

---

## 23. Тест-кейсы

### Позитивные
1. Нормализация EIS intake record
2. Нормализация manual opportunity
3. Нормализация private portal payload
4. Правильный parsing deadline
5. Правильный parsing budget/currency
6. Создание `tender_normalized`
7. Re-normalization после обновления source mapping

### Негативные
8. Недоступен raw payload
9. Пустой title после нормализации
10. Некорректный deadline format
11. Бюджет не распознан, но ошибочно поставлено число
12. Missing fields не отражены в quality block
13. Downstream получил source-specific raw вместо normalized payload

---

## 24. ТЗ для Codex / разработчика

### Задача
Реализовать модуль `M-008 Нормализация закупки` как canonical normalization layer между intake и screening.

### Нужно сделать
1. Спроектировать schema normalized tender payload.
2. Реализовать source-specific field mapping.
3. Реализовать normalization record.
4. Реализовать completeness_score.
5. Реализовать normalization_confidence.
6. Реализовать missing/ambiguous field tracking.
7. Реализовать `requires_manual_review`.
8. Реализовать emit `tender_normalized`.
9. Реализовать re-normalization capability.
10. Реализовать normalization monitor UI.
11. Реализовать интеграцию с M-007, M-001, M-004, M-009 и M-051.

### Ограничения
- нельзя подменять missing fields выдуманными значениями;
- нельзя терять raw payload trace;
- нельзя делать downstream зависимым от source-specific структуры;
- нельзя считать normalization успешной без quality block;
- нельзя ломать pipeline из-за неполной, но потенциально полезной записи.

### Рекомендация по реализации
Подходит схема:
- таблица `normalized_tender_records`
- source mapping adapters
- normalization rules engine
- quality calculator
- warnings registry
- event emitter `tender_normalized`

Для MVP сначала поддержать нормализацию:
- EIS
- MANUAL
- PRIVATE_PORTAL

---

## 25. Следующий модуль после завершения

После завершения `M-008` логически идет:
- **M-009 Screening Engine**

Почему:
как только закупка приведена к каноническому формату, следующий шаг — первично решить, стоит ли вообще брать ее в работу и тратить ресурсы на глубокую проработку.
