# Zakupki.gov.ru SOAP Integration

## Назначение

`zakupki_gov_ru_soap` добавляет в Tender Operator Agent Demo безопасный read-only источник для поиска закупок и получения публичной документации через SOAP-контур ЕИС.

Это не production crawler и не автономный бот. Источник используется только как controlled demo/pilot intake layer перед существующим Upload & Analyze pipeline.

## Безопасный read-only режим

Разрешено:

- искать публичную информацию о закупках;
- читать карточку закупки;
- получать список публичных вложений;
- скачивать разрешённые документы в локальный demo-run;
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
- `ZAKUPKI_GOV_RU_SOAP_TOKEN`
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
ZAKUPKI_GOV_RU_SOAP_TOKEN=ВСТАВИТЬ_ТОКЕН_СЮДА
ZAKUPKI_GOV_RU_SOAP_BASE_URL=https://int44.zakupki.gov.ru/eis-integration/services-vbs
ZAKUPKI_GOV_RU_SOAP_SEARCH_ACTION=searchProcurements
ZAKUPKI_GOV_RU_SOAP_DETAILS_ACTION=getProcurementDetails
ZAKUPKI_GOV_RU_SOAP_ATTACHMENTS_ACTION=listAttachments
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
- live network result зависит от фактического service path ЕИС, поэтому `base_url` и SOAP actions оставлены полностью конфигурируемыми.

## Как включить источник

1. Создать `.env.local` локально.
2. Вставить токен в `ZAKUPKI_GOV_RU_SOAP_TOKEN`.
3. Выполнить `set -a && source .env.local && set +a`.
4. Запустить backend.
5. Открыть `/demo/tender-agent`.
6. В режиме `Найти закупку` выбрать источник `zakupki_gov_ru_soap`.

Если endpoint/WSDL отличается, меняйте только `ZAKUPKI_GOV_RU_SOAP_BASE_URL`. Не хардкодьте URL в коде.

## Проверенные SOAP methods

В controlled pilot слое сейчас калибруются три action name:

- `searchProcurements`
- `getProcurementDetails`
- `listAttachments`

Они не зашиты жёстко и могут быть переопределены env-переменными, если фактический SOAP service использует другие action names.

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
3. Выбрать источник `zakupki_gov_ru_soap`.
4. Ввести запрос, например `электротехническое оборудование`.
5. Нажать `Найти закупки`.

API:

```bash
curl -s http://127.0.0.1:8000/api/demo/tender-agent/procurement/search \
  -H 'content-type: application/json' \
  -d '{"source":"zakupki_gov_ru_soap","query":"электротехническое оборудование","max_results":10}'
```

## Фактический статус live calibration

На текущем MacBook batch подтвердил следующее:

- `search`: local mapping и parsing покрыты тестами и проходят на real-shaped fixtures;
- `details`: local mapping и partial fallback покрыты тестами и проходят;
- `attachments`: local mapping и manual-upload fallback покрыты тестами и проходят;
- `download`: безопасный downloader работает только для разрешённых `http/https` вложений и не включается без валидного download URL;
- `live smoke`: был выполнен с локальным `.env.local`, а при проблемах с endpoint возвращает только sanitized diagnostic error без утечки токена.

Если ЕИС отвечает transport error или service path не совпадает с фактическим endpoint, procurement run не притворяется полным: UI показывает диагностический статус и переводит оператора в manual upload path.

## Как создать run из закупки

```bash
curl -s http://127.0.0.1:8000/api/demo/tender-agent/runs/from-procurement \
  -H 'content-type: application/json' \
  -d '{"source":"zakupki_gov_ru_soap","procurement_id":"NOTICE_ID","query":"электротехническое оборудование","download_attachments":true}'
```

Run сохраняется в:

```text
company_agent_runs/tender_operator_demo/{run_id}/
```

## Как скачать документацию

Скачивание выполняется только внутри `runs/from-procurement` и только для разрешённых вложений:

- `.pdf`
- `.docx`
- `.xlsx`
- `.xls`
- `.txt`
- `.csv`
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
ZAKUPKI_GOV_RU_SOAP_LIVE_TEST=1 ./.venv/bin/python -m pytest -q tests/test_tender_operator_agent_zakupki_soap_client.py -k live
```

В обычном CI/pytest live network не требуется.

## Диагностика

Безопасные диагностические артефакты пишутся локально в:

```text
company_agent_runs/zakupki_soap_live_diagnostics/
```

Используются:

- `last_status.json` — безопасный статус последнего вызова без токена;
- `last_error.txt` — sanitized transport/service error;
- `last_request.xml` и `last_response.xml` — только если `ZAKUPKI_GOV_RU_SOAP_DEBUG=1`, с замаскированным токеном.

UI показывает этот статус в карточке `Диагностика ЕИС`.

Если в диагностике видно `last_status=error`, оператор должен:

1. проверить `ZAKUPKI_GOV_RU_SOAP_BASE_URL`;
2. проверить нужен ли proxy или, наоборот, мешают системные proxy env;
3. повторить live smoke;
4. при необходимости перейти в `demo_local` или ручную загрузку документов.

## Known limitations

- SOAP envelope и parsing рассчитаны на controlled pilot и могут потребовать уточнения после фактических ответов ЕИС.
- Generic `https://int44.zakupki.gov.ru/eis-integration/services-vbs` path может требовать дополнительной service-path калибровки для реального live search на конкретной машине.
- PDF/DOCX/OCR извлечение остаётся ограниченным текущими parser utilities.
- ZIP обрабатывается только по существующим safe rules.
- Нет scheduled monitoring.
- Нет live SSE feed; UI показывает static event log после действий.
- Нет production-grade fuzzy matching закупок и документации.
