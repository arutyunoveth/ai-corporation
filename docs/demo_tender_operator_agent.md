# Tender Operator Agent Demo

## Что показывает демо

`Tender Operator Agent Demo` остаётся внутренним `demo / pilot`-контуром для controlled tender workflow.

Это не “автономный бот”, а операторская консоль, которая показывает один день работы тендерного агента:

- поиск закупки;
- выбор закупки;
- получение документации или честный переход к ручной загрузке;
- анализ документов;
- извлечение требований;
- подготовка вопросов и RFQ;
- нормализация ТКП;
- экономика;
- риски;
- рекомендация человеку.

Критичные действия по-прежнему не автоматизируются:

- нет подачи заявки;
- нет отправки email;
- нет действий на ЭТП;
- нет ЭЦП;
- нет cloud LLM;
- нет логина на площадки;
- нет обхода captcha;
- нет authenticated scraping.

## Режимы работы

Страница: `http://localhost:8000/demo/tender-agent`

### Режим 1: Найти закупку

Первый визуальный режим демо.

Показывает безопасный procurement discovery/intake слой:

- поиск работает в режиме только чтения;
- оператор видит найденные карточки закупок;
- может выбрать закупку;
- если demo-local документация доступна, она копируется в локальный run;
- если документация недоступна автоматически, создаётся run со статусом `docs_required`.

Поддерживаемые источники:

- `demo_local` — основной offline-safe источник для стабильной демонстрации;
- `mos_portal_public_api` — отображается как `disabled / experimental`, потому что идея взята из старого `tender-app`, но для включения нужен отдельный сетевой аудит.

### Режим 2: Загрузка и анализ

Controlled demo/pilot режим для локальной загрузки файлов закупки.

Пользователь может:

- ввести название закупки;
- выбрать категорию;
- указать заказчика;
- задать demo-параметры экономики;
- загрузить локальные документы;
- создать `run_id`;
- запустить анализ;
- увидеть pipeline, статусы, ограничения, event log и HTML report.

Если procurement run был создан без документации, в этом же operator console можно вручную добавить документы в уже созданный run.

### Режим 3: Демо-данные

Synthetic walkthrough на стабильных JSON fixtures из:

`demo_data/tender_operator_agent/`

Нужен для полностью повторяемого customer demo без зависимости от внешних сайтов и реальных документов.

## Поддерживаемые endpoints

### Synthetic demo

- `GET /demo/tender-agent`
- `GET /demo/tender-agent/report`
- `GET /api/demo/tender-agent/run`
- `GET /api/demo/tender-agent/steps`
- `GET /api/demo/tender-agent/report`
- `GET /api/demo/tender-agent/report/download`

### Procurement search / intake

- `GET /api/demo/tender-agent/procurements/search`
- `POST /api/demo/tender-agent/runs/from-procurement`
- `GET /api/demo/tender-agent/runs/{run_id}/procurement`

### Upload & Analyze

- `GET /api/demo/tender-agent/runs`
- `POST /api/demo/tender-agent/runs`
- `POST /api/demo/tender-agent/runs/{run_id}/files`
- `GET /api/demo/tender-agent/runs/{run_id}`
- `POST /api/demo/tender-agent/runs/{run_id}/analyze`
- `GET /api/demo/tender-agent/runs/{run_id}/steps`
- `GET /api/demo/tender-agent/runs/{run_id}/report`
- `GET /api/demo/tender-agent/runs/{run_id}/report/download`
- `GET /demo/tender-agent/runs/{run_id}`
- `GET /demo/tender-agent/runs/{run_id}/report`

## Как работает безопасный procurement discovery

На этом спринте включён только `demo_local`.

Он:

- не требует интернета;
- возвращает синтетические закупки;
- у части закупок даёт demo attachments;
- у части закупок честно помечает `manual_upload_required`, `unavailable_in_demo` или `source_requires_authorization`.

Система явно показывает:

- источник;
- номер закупки;
- дату публикации;
- срок подачи;
- цену, если есть;
- статус документации;
- можно ли продолжить автоматически или нужен ручной upload.

## Когда нужен ручной upload

Ручная загрузка требуется, если:

- документация не подготовлена в `demo_local`;
- источник в реальном мире потребовал бы авторизацию;
- в demo-контуре недоступно безопасное автоматическое скачивание;
- оператор хочет заменить demo-документы на собственный локальный пакет.

В таком случае run получает статус:

`docs_required`

После этого оператор вручную добавляет документы в этот же run и переводит его в `ready_to_analyze`.

## Поддерживаемые форматы файлов

- `.pdf`
- `.docx`
- `.xlsx`
- `.xls`
- `.txt`
- `.csv`
- `.zip`

Safe local storage:

- имена файлов нормализуются;
- path traversal не сохраняется;
- исполняемые форматы отклоняются;
- действуют лимиты на размер файла и общий объём;
- абсолютные server paths не показываются в UI.

## Как работает XLSX normalization

Детерминированный parser живёт в:

`src/modules/tender_operator_agent_demo/quote_normalizer.py`

Он:

- читает `.xlsx` через `openpyxl`;
- проверяет все листы;
- ищет строку заголовков по синонимам;
- извлекает позиции;
- классифицирует таблицу как `supplier_quote`, `customer_specification`, `price_table` или `unknown_table`;
- вместо падения выдаёт `partial`, `blocked` или `needs_review`, если структура нестандартная.

Поддерживаются типовые русские и английские колонки:

- номер / item;
- наименование / description;
- количество / quantity;
- ед. изм. / unit;
- цена / unit price;
- сумма / amount;
- срок поставки / delivery;
- производитель / manufacturer;
- валюта / currency.

## Как считается economics в demo mode

Для uploaded/procurement runs экономика считается только по локальным данным.

Используются:

- `target_margin_percent`;
- `logistics_reserve_percent`;
- `risk_reserve_percent`;
- `payment_delay_days`.

Система считает:

- `supplier_cost_min`;
- `supplier_cost_selected`;
- `preliminary_bid_price`;
- `gross_margin_amount`;
- `gross_margin_percent`;
- `logistics_reserve`;
- `risk_reserve`;
- `cash_gap_estimate`;
- `economics_status`.

Если цены или структурированных ТКП нет, система не выдумывает выручку и честно показывает:

- `blocked`;
- `insufficient_data`;
- `manual_review_required`.

## Что runner делает сейчас

Для uploaded/procurement mode используется controlled adapter вокруг:

`scripts/run_tender_operator_pilot.py`

Реально используются importable части текущей логики:

- requirements extraction;
- calibrated contract risk;
- supplier questions;
- deterministic quote normalization;
- demo economics summary;
- preliminary bid recommendation.

Shell subprocess с пользовательским вводом не используется.

## Event trace

Для каждого procurement/uploaded run создаётся:

`company_agent_runs/tender_operator_demo/{run_id}/events.jsonl`

Там сохраняются события:

- `procurement_search_started`
- `procurement_search_completed`
- `procurement_selected`
- `attachments_download_started`
- `attachment_saved`
- `attachments_download_completed`
- `manual_upload_required`
- `manual_upload_received`
- `run_created_from_procurement`
- `analysis_started`
- `analysis_completed`
- `analysis_blocked`

Сейчас UI показывает static event log после действий. Live SSE не включён в этом спринте.

## Где хранятся runs

`company_agent_runs/tender_operator_demo/{run_id}/`

Структура:

- `input/` — загруженные или safely-fetched документы;
- `normalized/` — извлечённый текст, если он доступен;
- `procurement/` — procurement metadata, source summary и attachments manifest;
- `output/` — JSON outputs и `report.html`;
- `metadata.json` — run metadata и safety flags;
- `events.jsonl` — event trace.

## Tender-app reuse audit

Отдельный аудит старого проекта:

`docs/product/tender_app_reuse_audit.md`

Короткий вывод:

- безопасно переиспользованы идеи read-only поиска и фильтрации документации;
- не переносились browser fallback, авторизация, cookies, Playwright и real-network контур;
- реальный источник пока не включён по умолчанию.

## Customer demo script

1. Открываем `/demo/tender-agent`.
2. На вкладке `Найти закупку` вводим `электротехническое оборудование`.
3. Получаем список закупок из `demo_local`.
4. Выбираем закупку.
5. Если документация доступна, создаётся run и копируется в локальный `input/`.
6. Если документация недоступна, интерфейс честно просит ручную загрузку.
7. Переходим в operator console, запускаем анализ.
8. Показываем pipeline: поиск закупки → документация → требования → вопросы → RFQ → ТКП → экономика → риски → решение.
9. Показываем event log.
10. Открываем HTML report.

## Что можно показывать заказчику

- controlled operator workflow;
- synthetic и локальные данные;
- procurement search в safe read-only режиме;
- честный `human-in-the-loop`;
- manual upload fallback;
- quote comparison;
- economics;
- trace / rationale;
- HTML report.

## Что нельзя обещать заказчику

- автономную подачу заявки;
- работу под логином на ЭТП;
- обход captcha;
- отправку писем поставщикам;
- ЭЦП;
- production crawler;
- массовый мониторинг закупок;
- полностью автоматическое юридически значимое действие.

## Known limitations

- реальный внешний источник не включён по умолчанию;
- `demo_local` остаётся основным стабильным источником;
- `.xls` работает ограниченно;
- сложные Excel layout’ы могут уходить в `partial` или `needs_review`;
- live SSE feed пока не реализован;
- procurement link ingestion по произвольной публичной ссылке пока не включён.

## Следующий спринт

- live event feed через SSE или polling;
- безопасный read-only анализ публичной ссылки на закупку;
- отдельный audited connector для одного реального публичного источника;
- история поисковых запросов и run’ов;
- мониторинг новых закупок по ключевым словам в read-only режиме.
