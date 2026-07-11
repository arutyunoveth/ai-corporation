# Tender Operator Agent Demo

## Что показывает демо

`Tender Operator Agent Demo` — операторская консоль с двумя основными режимами:

### Режим 1: Быстрый разбор закупки (Reseller Triage) — основной сценарий

Search-first режим для тендерных компаний-реселлеров:

- поиск закупок по ключевому слову;
- отображение количества найденных результатов;
- автоматический выбор самой свежей закупки;
- скоринг и решение GO / NO-GO / NEEDS REVIEW / LOW PRIORITY;
- стоп-факторы и рекомендация менеджеру.

Подробнее: [docs/mvp/tender_triage_reseller_mvp.md](mvp/tender_triage_reseller_mvp.md)

### Режим 2: Полный controlled tender workflow (demo/pilot-контур)

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

### Режим 1: Быстрый разбор закупки (Reseller Triage) — основной

Первый визуальный режим демо. Search-first сценарий для реселлеров.

- поиск закупок по ключевому слову;
- фильтры: закон, регион, НМЦК, дата публикации;
- отображение количества найденных результатов;
- автоматический выбор самой свежей закупки;
- скоринг 0–100 и решение GO / NO-GO / NEEDS REVIEW / LOW PRIORITY;
- стоп-факторы с severity: info / warning / critical;
- рекомендация менеджеру.

За один демо-цикл анализируется только одна закупка — самая свежая из результатов.

### Режим 2 (вкладка: Анализ по номеру): Получение документации

Отдельный intake-режим для получения документации по номеру закупки.

- поиск закупки и получение документации намеренно разделены;
- `getDocsIP` не используется как keyword search;
- оператор сначала находит закупку, затем вставляет реестровый номер;
- если `archiveUrl` получен, архив документации скачивается в read-only режиме и safely обрабатывается локально;
- если `archiveUrl` не получен, run честно переходит в `docs_required`.

### Режим 3: Загрузить документы

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

### Режим 4 (отдельная вкладка): Демо-данные

Synthetic walkthrough на стабильных JSON fixtures из:

`demo_data/tender_operator_agent/`

Нужен для полностью повторяемого customer demo без зависимости от внешних сайтов и реальных документов.

### Режим 5: Профиль поставщика и оценка релевантности (вкладка)

Детерминированная rule-based оценка релевантности закупок под профиль поставщика.

**Профиль поставщика:**
- Хранится как Pydantic-модель с категориями, регионами, ценовым диапазоном, ключевыми словами, стоп-словами, сертификатами и риск-профилем.
- Демо-профиль: «Демо-поставщик электротехнического оборудования» (категории: электротехника, кабель, шкафы управления; регионы: Москва и МО; цены: 100k–15M руб.).
- Вкладка «Профиль поставщика» в UI для просмотра и сброса.
- API: `GET /api/demo/tender-agent/supplier-profile`, `POST /api/demo/tender-agent/supplier-profile/reset`.

**Оценка релевантности карточки (preliminary):**
- Выполняется в `search_public_44fz()` для каждой найденной карточки.
- Измерения: ключевые слова (до 40 баллов), цена (до 20), дедлайн (до 10), риски (15), штраф стоп-слов (-15 каждое).
- Пороги: High >= 65, Medium >= 40, Low >= 20, Not Recommended < 20.
- Результат показывается в UI на карточке закупки: бейдж с процентом, разбивка по измерениям, причины.

**Оценка релевантности документов (после извлечения):**
- Выполняется в `analyze_uploaded_demo_run()` после распаковки архива.
- Сопоставляет ключевые слова и сертификаты поставщика с текстом документов.
- Результат записывается в `document_relevance` в метаданных run и в ответе `GET /api/demo/tender-agent/runs/{run_id}`.

**Ограничения:**
- Только rule-based (без ML/LLM).
- Стемминг: 7-символьный префикс + substring match для базовой русской морфологии.
- Профиль только в памяти сессии, не сохраняется между перезагрузками.

## Поддерживаемые endpoints

### Reseller Triage (search-first)

- `POST /api/demo/tender-agent/reseller/search-and-triage` — поиск и разбор свежей закупки
  - возвращает `source_type` (live/demo/unknown), `source_label`, `fallback_used`, `source_notice`, `total_count_kind`, `selection_reason`
  - возвращает `tender_card` (карточка закупки), `line_items` (позиции поставки), `has_line_items`

### Synthetic demo

- `GET /demo/tender-agent`
- `GET /demo/tender-agent/report`
- `GET /api/demo/tender-agent/run`
- `GET /api/demo/tender-agent/steps`
- `GET /api/demo/tender-agent/report`
- `GET /api/demo/tender-agent/report/download`

### Supplier profile

- `GET /api/demo/tender-agent/supplier-profile`
- `POST /api/demo/tender-agent/supplier-profile/reset`

### Procurement search / intake

- `GET /api/demo/tender-agent/procurements/search`
- `GET /api/demo/tender-agent/procurement/sources`
- `GET /api/demo/tender-agent/procurement/public-search-url`
- `POST /api/demo/tender-agent/procurement/public-44fz-search`
- `POST /api/demo/tender-agent/procurement/search`
- `GET /api/demo/tender-agent/procurement/{source}/{procurement_id}`
- `POST /api/demo/tender-agent/runs/from-procurement`
- `POST /api/demo/tender-agent/runs/from-eis-docs-archive`
- `POST /api/demo/tender-agent/runs/from-search-result`
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

## Интеграция с ЕИС

Для токена физического лица default-сценарий теперь такой:

1. Поиск закупки через `demo_local` или public HTML fallback.
2. Получение документации через `zakupki_gov_ru_getdocs_ip`.

Legacy `services-vbs` сохранён только как experimental legal-entity mode и не используется как default для текущего пользователя.

Он:

- выключен по умолчанию;
- включается только через `.env.local`;
- не хранит токен в коде или git;
- не логинится в личный кабинет;
- не использует cookies;
- не обходит captcha;
- не подаёт заявки;
- не отправляет email;
- не использует ЭЦП.

Локальная настройка:

```bash
cat > .env.local <<'EOF'
ZAKUPKI_GOV_RU_SOAP_ENABLED=1
ZAKUPKI_GOV_RU_SOAP_TOKEN_OWNER=individual
ZAKUPKI_GOV_RU_SOAP_TOKEN=ВСТАВИТЬ_ТОКЕН_СЮДА
ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_BASE_URL=https://int.zakupki.gov.ru/eis-integration/services/getDocsIP
ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_XSD_URL=https://int.zakupki.gov.ru/eis-integration/services/getDocsIP?xsd=getDocsIP-ws-api.xsd
ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_NAMESPACE=http://zakupki.gov.ru/fz44/get-docs-ip/ws
ZAKUPKI_GOV_RU_SOAP_TOKEN_HEADER_NAME=individualPerson_token
ZAKUPKI_GOV_RU_SOAP_MODE=PROD
ZAKUPKI_GOV_RU_SOAP_DISABLE_PROXY_FOR_EIS=1
ZAKUPKI_GOV_RU_SOAP_REQUIRE_DIRECT_RU_ROUTE=1
ZAKUPKI_GOV_RU_SOAP_ALLOWED_HOSTS=zakupki.gov.ru,.zakupki.gov.ru,int.zakupki.gov.ru,int44.zakupki.gov.ru,int44-ttls-cert.zakupki.gov.ru
ZAKUPKI_GOV_RU_SOAP_USER_AGENT=ArvectumTenderAgent/0.1 read-only
ZAKUPKI_GOV_RU_SOAP_CONTENT_TYPE=text/xml; charset=utf-8
ZAKUPKI_GOV_RU_SOAP_USE_SOAP_ACTION=1
ZAKUPKI_GOV_RU_SOAP_SOAP_ACTION=http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip
ZAKUPKI_GOV_RU_SOAP_TIMEOUT_SECONDS=30
ZAKUPKI_GOV_RU_SOAP_MAX_RESULTS=10
ZAKUPKI_GOV_RU_SOAP_MAX_ATTACHMENTS=20
ZAKUPKI_GOV_RU_SOAP_MAX_DOWNLOAD_MB=200
ZAKUPKI_GOV_RU_SOAP_TRUST_ENV_PROXY=0
ZAKUPKI_GOV_RU_SOAP_DEBUG=0
EOF

set -a
source .env.local
set +a
```

`.env.local` не коммитить.

Если фактический endpoint/WSDL отличается, меняется только env-конфигурация. Реальный токен нигде не печатается и не попадает в UI, events, report или diagnostics.

Текущий live calibration делался локально на MacBook. Токен используется только из `.env.local`, а UI, events, report и diagnostics показывают только факт наличия токена, но не его значение.

## Как работает безопасный procurement discovery

`demo_local`:

- не требует интернета;
- возвращает синтетические закупки;
- у части закупок даёт demo attachments;
- у части закупок честно помечает `manual_upload_required`, `unavailable_in_demo` или `source_requires_authorization`.

`public_eis_html_44fz`:

- используется как read-only публичный поиск по 44-ФЗ;
- формирует безопасный URL поиска ЕИС;
- пытается загрузить и распарсить публичную HTML-страницу выдачи;
- при успешном парсинге показывает карточки закупок;
- различает исходы `success_with_results`, `success_empty`, `source_unavailable`, `source_error`, `unsupported_search_mode`, `validation_error`;
- не маскирует `js_heavy`, `timeout`, `network_error`, `captcha_or_blocked` и ошибки парсинга под “0 результатов”;
- из карточек извлекается reestrNumber для handoff в getDocsIP;
- если HTML не парсится или ЕИС отдаёт JS-heavy/captcha/blocked страницу — честно показывает ссылку «Открыть поиск в ЕИС», сообщение о проблеме источника и кнопку `Открыть демо-закупку 0323100010326000013`;
- не обходит captcha, не использует cookies, не делает POST-действий;
- не превышает лимиты: таймаут 15 секунд, макс. размер ответа 5 MB.

`public_eis_html_223fz`:

- используется только как read-only fallback для поиска;
- может вернуть ссылку на публичную выдачу ЕИС;
- отдельный parser не включён в этом спринте.

`zakupki_gov_ru_getdocs_ip`:

- не является keyword search source;
- показывает disabled/configuration reason, если env/token не настроены;
- при включении выполняет read-only SOAP getDocsIP flow по номеру закупки;
- игнорирует системные proxy env по умолчанию, чтобы не зависеть от локальных `HTTP_PROXY` / `HTTPS_PROXY`, если это ломает доступ к ЕИС;
- для MacBook с системным PAC рекомендуется отдельное правило `DIRECT` для `zakupki.gov.ru` и `*.zakupki.gov.ru`;
- использует SOAP Header `individualPerson_token`;
- при скачивании архива передаёт `individualPerson_token` уже в HTTP header;
- создаёт procurement run через тот же downstream pipeline.

Система явно показывает:

- источник;
- номер закупки;
- дату публикации;
- срок подачи;
- цену, если есть;
- статус документации;
- можно ли продолжить автоматически или нужен ручной upload.
- в UI поиска отображается предупреждение: «Поиск работает в read-only режиме. Система не входит в личный кабинет, не обходит captcha, не подаёт заявку. Система только получает публичную документацию и готовит анализ для человека.».

## Ручная загрузка как fallback

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

## Журнал работы агента

Для каждого procurement/uploaded run создаётся:

`company_agent_runs/tender_operator_demo/{run_id}/events.jsonl`

Там сохраняются события:

- `procurement_search_started`
- `procurement_search_completed`
- `procurement_details_loaded`
- `attachments_list_loaded`
- `procurement_selected`
- `attachments_download_started`
- `attachment_saved`
- `attachment_skipped`
- `attachments_download_completed`
- `manual_upload_required`
- `manual_upload_received`
- `run_created_from_procurement`
- `analysis_started`
- `analysis_completed`
- `analysis_blocked`

Каждое событие содержит:

- `event_type`;
- `timestamp`;
- `message_ru`;
- `step`;
- `severity`;
- `metadata`.

UI показывает блок `Журнал работы агента`. Live SSE не включён в этом спринте.

## Диагностика ЕИС

Диагностика хранится локально в:

`company_agent_runs/zakupki_soap_diagnostics/`

Если ЕИС недоступен, система автоматически переключается на демо-набор и показывает предупреждение: «Источник поиска временно недоступен. Используется демо-набор для демонстрации сценария.»

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
- реальный SOAP-источник включается только через env и токен пользователя.

## Сценарий показа заказчику — Reseller Triage (основной)

1. Открываем `/demo/tender-agent`.
2. Основная вкладка — `Быстрый разбор закупки`.
3. Вводим запрос: `электротехническое оборудование`.
4. Система показывает:
   - количество найденных закупок (из демо-набора или публичного поиска);
   - бейдж источника: «Демо-набор» или «Публичный поиск»;
   - свёрнутую карточку самой свежей закупки.
5. Автоматически запускается скоринг:
   - оценка 0–100 (6 компонентов: товар, спецификация, коммерческие условия, дедлайн, документация, риски);
   - финальное решение: GO / NEEDS REVIEW / LOW PRIORITY / NO-GO;
   - стоп-факторы с severity: info / warning / critical;
   - рекомендация менеджеру.
6. Показываем карточку закупки (заказчик, закон, НМЦК, даты, регион, место и срок поставки).
7. Показываем позиции поставки (наименование, количество, единица, цена).
8. Расшифровываем скоринг с разбивкой по компонентам и причиной решения.
9. Если клиент спрашивает про демо-режим: «Сейчас используется демонстрационный набор данных для стабильной работы без интернета. В продукте поиск будет выполняться по живым данным ЕИС.»

## Сценарий показа заказчику — полный pipeline

10. Если нужно показать полный цикл анализа, переключаемся на вкладку `Анализ по номеру` или `Загрузить документы`.
11. Используем публичный поиск ЕИС (вкладка `Найти закупку`) или вставляем `reestrNumber` вручную.
12. Нажимаем `Получить документацию из ЕИС`.
13. Показываем карточку результата: `SOAP OK`, `archiveUrl получен`, `архив скачан`, `распаковано документов`.
14. Открываем run.
15. Если анализ не был запущен автоматически, нажимаем `Запустить анализ`.
16. Показываем pipeline: поиск закупки → документация → требования → вопросы → RFQ → ТКП → экономика → риски → решение.
17. Показываем `Журнал работы агента`, который обновляется через polling.
18. Открываем HTML report.

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

### Reseller Triage

- **Только одна закупка за цикл:** система выбирает самую свежую (по дате публикации) — клиент не может выбрать произвольную закупку из выдачи.
- **Только одна анализируемая закупка:** нет пакетного скоринга всех результатов.
- **Отбор по дате:** если у двух закупок одинаковая дата публикации — берётся первая найденная (порядок из поиска). Если дат нет — выбирается первый результат с предупреждением.
- **Демо-данные по умолчанию:** `demo_local` — основной источник; `public_eis_html_44fz` — опциональный live-источник без гарантии парсинга.
- **Скоринг rule-based:** без LLM/ML. 6 компонентов, детерминированный.

### Общие

- SOAP-источник ЕИС не включён по умолчанию и требует локальный токен;
- getDocsIP и public search intentionally разделены;
- `demo_local` остаётся основным стабильным источником;
- public HTML fallback пока не делает полноценный parser выдачи;
- 223-ФЗ требует отдельного parser path и не смешивается с 44-ФЗ getDocsIP;
- XML order для `getDocsByReestrNumberRequest` критичен;
- архив в ЕИС может формироваться асинхронно, поэтому возможен статус `archive_not_ready`;
- если `archiveUrl` не получен, система переходит в manual upload fallback;
- `.xls` работает ограниченно;
- сложные Excel layout’ы могут уходить в `partial` или `needs_review`;
- live SSE feed пока не реализован, используется polling event feed;
- procurement link ingestion по произвольной публичной ссылке пока не включён.

## Приоритет источника данных

Приоритетным источником структурированных данных является электронное извещение (epNotification XML). Метаданные карточки поиска используются как fallback, а прикреплённые документы — для детального анализа. В случае конфликта данных приоритет имеет извещение ЕИС. Даты в мастере отображаются в формате ДД.ММ.ГГГГ, НМЦК — в рублях с разделителями тысяч. В отчётах источник данных маркируется как «электронное извещение ЕИС» или «карточка ЕИС».

## Troubleshooting

- Если `getDocsIP` не отвечает, сначала проверьте PAC/DIRECT-route и `NO_PROXY`.
- Если `archive_not_ready`, повторите скачивание позже: архив может ещё готовиться в ЕИС.
- Если run создан, но документов нет, используйте тот же run и ручную загрузку файлов.
- Полный archive URL/ticket умышленно не показывается в UI и report; для отладки используйте только sanitized host/path summary.

## Следующий спринт

- выбор произвольной закупки из выдачи (не только самой свежей);
- динамический фильтр цены, закона, региона на стороне поиска;
- live event feed через SSE или polling;
- безопасный read-only анализ публичной ссылки на закупку;
- отдельный audited connector для одного реального публичного источника;
- история поисковых запросов и run’ов;
- мониторинг новых закупок по ключевым словам в read-only режиме.
