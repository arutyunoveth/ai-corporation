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
- `public_eis_html_44fz` — публичный HTML fallback для 44-ФЗ;
- `public_eis_html_223fz` — публичный HTML fallback для 223-ФЗ;

### Режим 2: Получить документацию по номеру

Отдельный intake-режим для токена физического лица.

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

### Режим 4: Демо-данные

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
- `GET /api/demo/tender-agent/procurement/sources`
- `GET /api/demo/tender-agent/procurement/public-search-url`
- `POST /api/demo/tender-agent/procurement/search`
- `GET /api/demo/tender-agent/procurement/{source}/{procurement_id}`
- `POST /api/demo/tender-agent/runs/from-procurement`
- `POST /api/demo/tender-agent/runs/from-eis-docs-archive`
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

`public_eis_html_44fz` / `public_eis_html_223fz`:

- используются только как read-only fallback для поиска;
- могут вернуть ссылку на публичную выдачу ЕИС;
- не притворяются полноценным parser/search API.

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

Во вкладке `Найти закупку` есть отдельная карточка `Диагностика ЕИС`.

Она показывает безопасные поля:

- configured / token_present;
- endpoint host и path;
- последний SOAP action;
- `last_status=ok|error`;
- sanitized текст последней ошибки.

Диагностика хранится локально в:

`company_agent_runs/zakupki_soap_diagnostics/`

Если карточка показывает ошибку transport/service layer, это не приводит к ложному "зелёному" статусу анализа. Оператор видит проблему сразу и может:

- скорректировать `ZAKUPKI_GOV_RU_SOAP_BASE_URL`;
- проверить proxy-настройки;
- использовать `demo_local`;
- перейти к ручной загрузке документов.

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

## Сценарий показа заказчику

1. Открываем `/demo/tender-agent`.
2. Выбираем `Найти закупку`.
3. Источник: `demo_local` или public HTML fallback.
   Перед работой смотрим карточку `Диагностика ЕИС`: она сразу показывает, настроен ли локальный `getDocsIP`.
4. Вводим запрос: `электротехническое оборудование`.
5. Смотрим найденные закупки.
6. Открываем найденную закупку или публичный HTML fallback и копируем реестровый номер.
7. Переходим во вкладку `Получить документацию по номеру`.
8. Вставляем `reestrNumber`.
9. Нажимаем `Получить документацию из ЕИС`.
10. Показываем карточку результата: `SOAP OK`, `archiveUrl получен`, `архив скачан`, `распаковано документов`.
11. Открываем run.
12. Если анализ не был запущен автоматически, нажимаем `Запустить анализ`.
13. Показываем pipeline: поиск закупки → документация → требования → вопросы → RFQ → ТКП → экономика → риски → решение.
14. Показываем `Журнал работы агента`, который обновляется через polling.
15. Открываем HTML report.

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

## Troubleshooting

- Если `getDocsIP` не отвечает, сначала проверьте PAC/DIRECT-route и `NO_PROXY`.
- Если `archive_not_ready`, повторите скачивание позже: архив может ещё готовиться в ЕИС.
- Если run создан, но документов нет, используйте тот же run и ручную загрузку файлов.
- Полный archive URL/ticket умышленно не показывается в UI и report; для отладки используйте только sanitized host/path summary.

## Следующий спринт

- live event feed через SSE или polling;
- безопасный read-only анализ публичной ссылки на закупку;
- отдельный audited connector для одного реального публичного источника;
- история поисковых запросов и run’ов;
- мониторинг новых закупок по ключевым словам в read-only режиме.
