# Tender Operator Agent Demo

## Что это за демо

`Tender Operator Agent Demo` остаётся внутренним `demo / pilot`-контуром для controlled tender workflow.

Он показывает не “автономного бота”, а честный операторский сценарий:

- документы;
- требования;
- вопросы;
- RFQ;
- ТКП;
- экономика;
- риски;
- решение для человека.

Критичные действия по-прежнему не автоматизируются:

- нет подачи заявки;
- нет отправки email;
- нет действий на ЭТП;
- нет ЭЦП;
- нет cloud LLM;
- нет внешних интеграций.

## Режимы работы

На странице `http://localhost:8000/demo/tender-agent` теперь есть два режима.

### Demo dataset mode

Это прежний synthetic demo, собранный на стабильных данных из:

`demo_data/tender_operator_agent/`

Он нужен для предсказуемого показа сценария на встрече, когда нужен красивый и повторяемый walkthrough.

### Upload & Analyze mode

Это controlled demo/pilot режим для локальной загрузки файлов закупки.

Пользователь может:

- ввести название закупки;
- выбрать категорию;
- указать заказчика;
- загрузить локальные документы;
- создать `run_id`;
- запустить анализ;
- увидеть pipeline, статусы, ограничения и итоговый отчёт.

## Как запустить локально

1. Создать окружение и установить зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

2. Если нужен полный backend-контур проекта, поднять PostgreSQL и применить миграции:

```bash
docker compose up -d
export AI_CORP_DATABASE_URL=postgresql+psycopg://ai_corporation:ai_corporation@localhost:5432/ai_corporation
alembic upgrade head
```

3. Запустить backend:

```bash
uvicorn src.main:app --reload
```

4. Открыть demo UI:

```text
http://localhost:8000/demo/tender-agent
```

## Поддерживаемые endpoints

### Synthetic demo

- `GET /demo/tender-agent`
- `GET /demo/tender-agent/report`
- `GET /api/demo/tender-agent/run`
- `GET /api/demo/tender-agent/steps`
- `GET /api/demo/tender-agent/report`
- `GET /api/demo/tender-agent/report/download`

### Upload & Analyze

- `GET /api/demo/tender-agent/runs`
- `POST /api/demo/tender-agent/runs`
- `GET /api/demo/tender-agent/runs/{run_id}`
- `POST /api/demo/tender-agent/runs/{run_id}/analyze`
- `GET /api/demo/tender-agent/runs/{run_id}/steps`
- `GET /api/demo/tender-agent/runs/{run_id}/report`
- `GET /api/demo/tender-agent/runs/{run_id}/report/download`
- `GET /demo/tender-agent/runs/{run_id}`
- `GET /demo/tender-agent/runs/{run_id}/report`

## Как загружать документы

В `Upload & Analyze` доступны поля:

- `tender_title`
- `tender_category`
- `customer_name`
- `notes`
- `files`

Поддержаны форматы:

- `.pdf`
- `.docx`
- `.xlsx`
- `.xls`
- `.txt`
- `.csv`
- `.zip`

### Demo dataset mode

Synthetic walkthrough из `demo_data/tender_operator_agent/` остаётся без изменений и подходит для полностью повторяемого показа на встрече.

### Upload & Analyze mode

Этот режим теперь умеет не только безопасно принимать файлы, но и:

- распознавать простые supplier quote Excel-таблицы;
- извлекать позиции, количества, цены и суммы;
- строить базовое сравнение поставщиков;
- считать demo economics на локальных данных и operator defaults;
- честно показывать `partial`, `blocked` и `needs_review`, если таблица нестандартная или данных недостаточно.

Загрузка проходит через safe local storage:

- имена файлов нормализуются;
- опасные пути не сохраняются;
- исполняемые форматы отклоняются;
- действуют лимиты на размер файла и общий объём;
- абсолютные server paths не показываются в UI.

## Где хранятся uploaded runs

Локальные demo-runs сохраняются в:

`company_agent_runs/tender_operator_demo/{run_id}/`

Структура:

- `input/` — загруженные файлы
- `normalized/` — извлечённый текст, если он доступен
- `output/` — JSON outputs и `report.html`
- `metadata.json` — run metadata и safety flags

## Что runner делает сейчас

Для uploaded mode используется controlled adapter вокруг существующего tender operator runner logic.

Источник логики:

- `scripts/run_tender_operator_pilot.py`

Используются importable части текущего runner flow:

- stub requirements extraction
- calibrated contract risk logic
- supplier questions
- TKP comparison placeholder
- economics placeholder
- preliminary bid decision logic

Это значит:

- runner reuse есть;
- shell subprocess для user input не используется;
- внешние команды не запускаются;
- real external execution не открывается.

## Как работает XLSX normalization

Новый deterministic parser живёт в:

`src/modules/tender_operator_agent_demo/quote_normalizer.py`

Он:

- читает `.xlsx` через `openpyxl`;
- проверяет все листы;
- ищет строку заголовков по синонимам;
- извлекает позиции;
- классифицирует таблицу как `supplier_quote`, `customer_specification`, `price_table` или `unknown_table`;
- строит warnings и limitations вместо падения.

### Поддерживаемые layout’ы

Лучше всего поддерживаются простые табличные layout’ы, где есть одна явная строка заголовков и дальше идут позиции.

Поддерживаются русские и английские синонимы для колонок:

- номер / item
- наименование / description
- количество / quantity
- ед. изм. / unit
- цена / unit price
- сумма / amount
- срок поставки / delivery
- производитель / manufacturer
- валюта / currency

### Required / optional columns

Для уверенного supplier quote extraction обычно нужны:

- наименование;
- количество или сумма;
- цена или сумма.

Опционально извлекаются:

- срок поставки;
- производитель;
- валюта;
- единица измерения.

### Known limitations по Excel

- `.xlsx` поддержан содержательно.
- `.xls` пока принимается, но даёт ограниченный deterministic fallback и warning.
- сложные merged-cell layout’ы, несколько таблиц на листе и нетипичные шапки могут уйти в `partial` или `needs_review`.
- fuzzy matching позиций намеренно ограничен, чтобы не рисовать ложную уверенность.

## Что такое fallback mode

Если uploaded package неполный или текст не извлекается полностью, включается:

`analysis_mode = "fallback_deterministic_adapter"`

Это происходит, например, когда:

- не удалось извлечь текст из PDF/DOCX;
- загружены только часть ключевых документов;
- нет ТКП;
- есть `.xlsx/.xls`, но текстовое извлечение для них ограничено.

В fallback mode система:

- не падает;
- сохраняет run;
- строит partial pipeline;
- честно показывает `blocked`, `partial`, `needs_review`;
- выдаёт предварительный report с limitations.

## Как считается economics в demo mode

В Upload & Analyze форме доступны operator defaults:

- `target_margin_percent`
- `logistics_reserve_percent`
- `risk_reserve_percent`
- `payment_delay_days`

Если есть распознанные supplier quote totals, система считает:

- `supplier_cost_min`
- `supplier_cost_selected`
- `logistics_reserve`
- `risk_reserve`
- `preliminary_bid_price`
- `cash_gap_estimate`

Если цены заказчика нет, система не выдумывает выручку и явно оставляет:

- `expected_revenue = unavailable`
- economics status как `insufficient_data` или `conditionally_viable`
- recommendation как human-reviewed outcome, а не auto-go.

## Что требует manual review

Система специально выносит в ручную проверку:

- позиции с низкой уверенностью;
- разные единицы измерения;
- разные валюты;
- отсутствующие сроки поставки;
- отсутствие цены заказчика;
- нестандартные Excel layout’ы;
- совместимость аналогов и сертификатов.

## Что автоматизировано, а что нет

### Что уже есть

- safe local upload
- safe run storage
- controlled analysis pipeline
- synthetic demo mode
- uploaded local run mode
- HTML report для uploaded runs
- list recent runs
- safety flags в metadata и UI

### Что не автоматизировано

- отправка поставщикам
- submission на ЭТП
- подписание документов
- ЭЦП
- email automation
- OCR
- cloud LLM
- final legal/financial approval

## Как показывать это заказчику

Рекомендуемый порядок:

1. Открыть synthetic demo и показать идеальный walkthrough.
2. Переключиться в `Upload & Analyze`.
3. Загрузить локальный пакет документов.
4. Создать `run_id`.
5. Запустить `Analyze`.
6. Показать, что система честно блокирует шаги без ТКП или без достаточного текста.
7. Открыть блок `Извлечённые ТКП`.
8. Показать `Сравнение предложений`.
9. Показать `Экономика` и manual checks.
10. Подчеркнуть `human-in-the-loop` и отсутствие внешних действий.

### Рекомендуемый customer-demo сценарий

1. Загрузить ТЗ или notice/technical spec.
2. Загрузить проект договора.
3. Загрузить 2–3 ТКП в `.xlsx`.
4. Нажать `Создать demo run`.
5. Запустить `Анализировать`.
6. Показать supplier quote extraction и comparison.
7. Показать economics и список ручных проверок.
8. Открыть HTML report в новой вкладке.

## Safety

Для uploaded runs интерфейс и metadata явно фиксируют:

- `human_in_the_loop = true`
- `external_actions = false`
- `no_platform_submission = true`
- `no_email_sending = true`
- `no_digital_signature = true`

## Known limitations

- `.xlsx` поддержан для простых quote/spec tables, но не для всех возможных layout’ов.
- `.xls` не получает полноценной нормализации и должен считаться partial path.
- `.pdf/.docx` извлекаются только в доступном локальном парсере; сложные документы могут уйти в partial/fallback.
- economics остаётся demo-mode оценкой, а не production finance module.
- report download сейчас отдает HTML artifact; PDF/DOCX export не делался в этом спринте.
- нет OCR, нет LLM extraction и нет production-grade fuzzy matching.

## Что сделано с падавшим dry-run test

Перед работой по upload/analyze был устранён отдельный red flag:

- локальные generated artifacts были найдены в `company_agent_runs/dry_run_0/exported_context/`
- они удалены из рабочего дерева
- `.gitignore` дополнен для соседнего generated output `operator_logs/`

Это позволило вернуть зелёный `tests/company_agents/test_company_agent_dry_run_setup.py`.

## Что нельзя обещать заказчику

- что агент сам подаст заявку;
- что система сама отправит RFQ или email;
- что economics является финальным финансовым заключением;
- что сравнение таблиц не требует operator review;
- что есть автономная работа на ЭТП или с ЭЦП.

## Следующие идеи

- улучшить поддержку `.xls` и более сложных табличных layout’ов
- вынести reusable runner adapter из script-level helpers в отдельный production-friendly module
- добавить ввод цены заказчика или bid target прямо в UI
- добавить export в PDF/DOCX поверх уже существующего HTML report
- добавить историю quote-normalization quality по uploaded runs
- сделать report export в PDF/DOCX на базе уже сформированного HTML
- добавить selector между несколькими uploaded runs и richer run history filters
