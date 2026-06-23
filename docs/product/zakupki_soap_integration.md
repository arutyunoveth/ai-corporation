# Zakupki.gov.ru SOAP Integration

## Назначение

В текущем rework-контуре интеграция ЕИС разделена на два разных сценария:

- Procurement Search: `demo_local` или public HTML fallback для поиска закупки.
- Documentation Intake: `zakupki_gov_ru_getdocs_ip` для получения публичной документации по реестровому номеру.

`getDocsIP` не используется как универсальный keyword search. Это read-only сервис получения документации по номеру закупки для токена физического лица.

## Безопасный read-only режим

Разрешено:

- искать публичную информацию о закупках через offline-safe demo или public HTML fallback;
- получать архив публичной документации через getDocsIP по реестровому номеру;
- скачивать разрешённый ZIP-архив в локальный demo-run;
- передавать эти документы в существующий локальный анализ.

Запрещено:

- логиниться в личный кабинет;
- использовать cookies/session state;
- обходить captcha;
- подавать заявки;
- использовать ЭЦП;
- отправлять email поставщикам;
- делать действия на ЭТП;
- вызывать платные/private API без отдельного разрешения.

## Env variables

Настройки читаются из environment variables:

- `ZAKUPKI_GOV_RU_SOAP_ENABLED`
- `ZAKUPKI_GOV_RU_SOAP_TOKEN_OWNER`
- `ZAKUPKI_GOV_RU_SOAP_TOKEN`
- `ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_BASE_URL`
- `ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_XSD_URL`
- `ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_NAMESPACE`
- `ZAKUPKI_GOV_RU_SOAP_TOKEN_HEADER_NAME`
- `ZAKUPKI_GOV_RU_SOAP_MODE`
- `ZAKUPKI_GOV_RU_SOAP_BASE_URL`
- `ZAKUPKI_GOV_RU_SOAP_SEARCH_ACTION`
- `ZAKUPKI_GOV_RU_SOAP_DETAILS_ACTION`
- `ZAKUPKI_GOV_RU_SOAP_ATTACHMENTS_ACTION`
- `ZAKUPKI_GOV_RU_SOAP_TIMEOUT_SECONDS`
- `ZAKUPKI_GOV_RU_SOAP_MAX_RESULTS`
- `ZAKUPKI_GOV_RU_SOAP_MAX_ATTACHMENTS`
- `ZAKUPKI_GOV_RU_SOAP_MAX_DOWNLOAD_MB`
- `ZAKUPKI_GOV_RU_SOAP_TRUST_ENV_PROXY`
- `ZAKUPKI_GOV_RU_SOAP_DEBUG`

Источник включается только если `ZAKUPKI_GOV_RU_SOAP_ENABLED=1` и токен не является placeholder.

## Куда вставить токен

Пользователь создаёт локальный файл `.env.local` самостоятельно:

```bash
cat > .env.local <<'EOF'
ZAKUPKI_GOV_RU_SOAP_ENABLED=1
ZAKUPKI_GOV_RU_SOAP_TOKEN_OWNER=individual
ZAKUPKI_GOV_RU_SOAP_TOKEN=ВСТАВИТЬ_ТОКЕН_СЮДА
ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_BASE_URL=https://int44.zakupki.gov.ru/eis-integration/services/getDocsIP
ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_XSD_URL=https://int44.zakupki.gov.ru/eis-integration/services/getDocsIP?xsd=getDocsIP-ws-api.xsd
ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_NAMESPACE=http://zakupki.gov.ru/fz44/get-docs-ip/ws
ZAKUPKI_GOV_RU_SOAP_TOKEN_HEADER_NAME=individualPerson_token
ZAKUPKI_GOV_RU_SOAP_MODE=PROD
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

Не вставляйте реальный токен в код, README, docs, тесты или git history.

## Локальная калибровка на MacBook

Текущий live calibration batch выполнялся локально на MacBook в репозитории `~/Documents/AI-Corporation`.

Практическое наблюдение из этого цикла:

- ambient proxy variables в macOS-сессии могут ломать SOAP transport;
- по умолчанию клиент поэтому игнорирует `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY`;
- если нужен корпоративный proxy, его можно вернуть через `ZAKUPKI_GOV_RU_SOAP_TRUST_ENV_PROXY=1`;
- для токена физлица default endpoint теперь `https://int44.zakupki.gov.ru/eis-integration/services/getDocsIP`;
- legacy `services-vbs` сохранён только как experimental legal-entity mode.

## Как включить источник

1. Создать `.env.local` локально.
2. Вставить токен в `ZAKUPKI_GOV_RU_SOAP_TOKEN`.
3. Выполнить `set -a && source .env.local && set +a`.
4. Запустить backend.
5. Открыть `/demo/tender-agent`.
6. Для поиска использовать `demo_local` или public HTML fallback.
7. Для документации использовать вкладку `Получить документацию по номеру`.

Если endpoint/WSDL отличается, меняйте только env-конфигурацию. Не хардкодьте URL в коде.

## Проверенные getDocsIP methods

В controlled pilot слое для токена физлица сейчас поддерживаются:

- `getDocsByReestrNumberRequest` — основной сценарий;
- `getDocsByOrgRegionRequest` — optional / experimental.

SOAP namespace:

- `http://zakupki.gov.ru/fz44/get-docs-ip/ws`

SOAP Header:

- `<individualPerson_token>...</individualPerson_token>`

HTTP header при скачивании архива:

- `individualPerson_token: <token>`

Порядок XML важен. Для `getDocsByReestrNumberRequest` сохраняется:

- `index -> selectionParams`
- внутри `selectionParams`: `subsystemType -> reestrNumber`

## Как запустить backend

```bash
./.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Demo UI:

```text
http://127.0.0.1:8000/demo/tender-agent
```

## Как выполнить поиск

UI:

1. Открыть `http://127.0.0.1:8000/demo/tender-agent`.
2. Выбрать вкладку `Найти закупку`.
3. Выбрать `demo_local` или `public_eis_html_44fz`.
4. Ввести запрос, например `электротехническое оборудование`.
5. Для public HTML fallback открыть ссылку ЕИС и скопировать реестровый номер выбранной закупки.

API:

```bash
curl -s "http://127.0.0.1:8000/api/demo/tender-agent/procurement/public-search-url?query=%D1%8D%D0%BB%D0%B5%D0%BA%D1%82%D1%80%D0%BE%D1%82%D0%B5%D1%85%D0%BD%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%BE%D0%B5%20%D0%BE%D0%B1%D0%BE%D1%80%D1%83%D0%B4%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5&law=44fz"
```

## Фактический статус live calibration

На текущем MacBook batch подтвердил следующее:

- `search`: отделён от SOAP и работает через `demo_local` или public HTML fallback;
- `getDocsByReestrNumber`: поддержан как основной getDocsIP сценарий;
- `archiveUrl`: парсится в controlled parser слое с честными статусами `completed / no_archive_url / validation_error / soap_fault / echo_request_unprocessed`;
- `download`: архив скачивается только как `zip` и только с `individualPerson_token` в HTTP header;
- `live smoke`: может завершиться transport/service error, но возвращает только sanitized diagnostics без утечки токена.

Если `archiveUrl` не получен или ЕИС отвечает transport/service error, procurement run не притворяется полным: UI показывает диагностический статус и переводит оператора в manual upload path.

## Как запросить архив документации по номеру

```bash
curl -s http://127.0.0.1:8000/api/demo/tender-agent/runs/from-eis-docs-archive \
  -H 'content-type: application/json' \
  -d '{"reestr_number":"0888200000224000038","law":"44fz","subsystem_type":"PRIZ","download_archive":true}'
```

Run сохраняется в:

```text
company_agent_runs/tender_operator_demo/{run_id}/
```

## Как скачать документацию

Скачивание выполняется только внутри `runs/from-eis-docs-archive` и только для ZIP-архива документации.

- `.zip`

Downloader проверяет:

- только `http/https`;
- allowlist доменов;
- расширение;
- размер одного файла;
- общий размер;
- количество файлов;
- безопасное имя файла;
- отсутствие path traversal.

## Что делать, если документы недоступны

Если документация не найдена или не может быть безопасно скачана:

- run создаётся со статусом `docs_required`;
- UI показывает manual upload fallback;
- report честно пишет: `Документация не получена. Анализ невозможен до ручной загрузки файлов.`;
- оператор вручную добавляет документы в тот же run;
- после этого можно запускать анализ.

## Что система НЕ делает

- Не подаёт заявки.
- Не подписывает документы.
- Не отправляет письма.
- Не входит на площадки под учётной записью.
- Не обходит captcha.
- Не использует Playwright для закрытых страниц.
- Не скрывает необходимость ручной проверки.

## Live smoke test

По умолчанию live SOAP tests пропущены.

Локальный smoke можно включить только вручную, когда env настроен:

```bash
set -a
source .env.local
set +a
ZAKUPKI_GOV_RU_SOAP_LIVE_TEST=1 ./.venv/bin/python -m pytest -q tests/test_tender_operator_agent_getdocs_ip_client.py -k live
```

В обычном CI/pytest live network не требуется.

## Диагностика

Безопасные диагностические артефакты пишутся локально в:

```text
company_agent_runs/zakupki_soap_diagnostics/
```

Используются:

- `last_status.json` — безопасный статус последнего вызова без токена;
- `last_error.txt` — sanitized transport/service error;
- `last_request.xml` и `last_response.xml` — только если `ZAKUPKI_GOV_RU_SOAP_DEBUG=1`, с замаскированным токеном.

UI показывает этот статус в карточке `Диагностика ЕИС`.

Если в диагностике видно `last_status=error`, оператор должен:

1. проверить `ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_BASE_URL`;
2. проверить нужен ли proxy или, наоборот, мешают системные proxy env;
3. повторить live smoke;
4. при необходимости перейти в `demo_local` или ручную загрузку документов.

## Known limitations

- SOAP envelope и parsing рассчитаны на controlled pilot и могут потребовать уточнения после фактических ответов ЕИС.
- public HTML search остаётся fallback/manual path, а не полноценным parser API;
- 223-ФЗ требует отдельного path/parser и не смешивается с 44-ФЗ getDocsIP;
- доступность `archiveUrl` зависит от фактического ответа ЕИС;
- PDF/DOCX/OCR извлечение остаётся ограниченным текущими parser utilities.
- ZIP обрабатывается только по существующим safe rules.
- Нет scheduled monitoring.
- Нет live SSE feed; UI показывает static event log после действий.
- Нет production-grade fuzzy matching закупок и документации.
