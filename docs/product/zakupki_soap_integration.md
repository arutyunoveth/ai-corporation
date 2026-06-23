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
- `ZAKUPKI_GOV_RU_SOAP_TIMEOUT_SECONDS`
- `ZAKUPKI_GOV_RU_SOAP_MAX_RESULTS`
- `ZAKUPKI_GOV_RU_SOAP_MAX_ATTACHMENTS`
- `ZAKUPKI_GOV_RU_SOAP_MAX_DOWNLOAD_MB`

Источник включается только если `ZAKUPKI_GOV_RU_SOAP_ENABLED=1` и токен не является placeholder.

## Куда вставить токен

Пользователь создаёт локальный файл `.env.local` самостоятельно:

```bash
cat > .env.local <<'EOF'
ZAKUPKI_GOV_RU_SOAP_ENABLED=1
ZAKUPKI_GOV_RU_SOAP_TOKEN=ВСТАВИТЬ_ТОКЕН_СЮДА
ZAKUPKI_GOV_RU_SOAP_BASE_URL=https://int44.zakupki.gov.ru/eis-integration/services-vbs
ZAKUPKI_GOV_RU_SOAP_TIMEOUT_SECONDS=30
ZAKUPKI_GOV_RU_SOAP_MAX_RESULTS=10
ZAKUPKI_GOV_RU_SOAP_MAX_ATTACHMENTS=20
ZAKUPKI_GOV_RU_SOAP_MAX_DOWNLOAD_MB=200
EOF

set -a
source .env.local
set +a
```

`.env.local` не коммитить.

Не вставляйте реальный токен в код, README, docs, тесты или git history.

## Как включить источник

1. Создать `.env.local` локально.
2. Вставить токен в `ZAKUPKI_GOV_RU_SOAP_TOKEN`.
3. Выполнить `set -a && source .env.local && set +a`.
4. Запустить backend.
5. Открыть `/demo/tender-agent`.
6. В режиме `Найти закупку` выбрать источник `zakupki_gov_ru_soap`.

Если endpoint/WSDL отличается, меняйте только `ZAKUPKI_GOV_RU_SOAP_BASE_URL`. Не хардкодьте URL в коде.

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
ZAKUPKI_GOV_RU_SOAP_LIVE_TEST=1 ./.venv/bin/python -m pytest tests/test_tender_operator_agent_zakupki_soap_client.py -q
```

В обычном CI/pytest live network не требуется.

## Known limitations

- SOAP envelope и parsing рассчитаны на controlled pilot и могут потребовать уточнения после фактических ответов ЕИС.
- PDF/DOCX/OCR извлечение остаётся ограниченным текущими parser utilities.
- ZIP обрабатывается только по существующим safe rules.
- Нет scheduled monitoring.
- Нет live SSE feed; UI показывает static event log после действий.
- Нет production-grade fuzzy matching закупок и документации.
