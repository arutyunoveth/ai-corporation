# Free Web Research Pipeline (Tender Research)

## What It Does

`src/tender_research/` — бесплатный/локальный слой накопления базы закупок и внешних сырых данных без платных API и без LLM-анализа.

Pipeline:
1. Получает закупки из ЕИС (через существующую SOAP-интеграцию или демо-данные)
2. Сохраняет закупки в локальную БД (SQLite/PostgreSQL)
3. Копит историю заказчиков
4. Скачивает документы закупки (PDF, DOCX, XLSX, TXT, HTML, ZIP)
5. Извлекает текст из документов
6. Генерирует поисковые запросы (без LLM, по шаблонам)
7. Выполняет бесплатный HTML-поиск (DuckDuckGo)
8. Открывает найденные страницы через requests или Playwright
9. Сохраняет сырые HTML, извлечённый текст, артефакты

## What It Does NOT Do

- Не использует Yandex Search API, OpenAI, Anthropic, платные SERP
- Не запускает локальную LLM
- Не делает embeddings, RAG, анализ рисков
- Не генерирует рекомендации
- Не отправляет письма поставщикам
- Не обходит капчи
- Не авторизуется на ЭТП
- Не делает OCR сканов

## Why Free / Local

Весь стек бесплатный:
- DuckDuckGo HTML — бесплатный поиск без API-ключа
- requests / Playwright — открытие страниц
- SQLite — БД без сервера
- pypdf, openpyxl, ElementTree — извлечение текста

## EIS Loader Mode

`src/tender_research/eis_loader.py` — `EisTenderLoader` supports two modes controlled by `AI_CORP_TENDER_RESEARCH_EIS_MODE`:

| Mode | Description |
|------|-------------|
| `demo` (default) | Returns 3 hardcoded demo tenders. No SOAP calls. Used for testing and CI. |
| `real` | Wraps `ZakupkiSoapClient` from the existing EIS SOAP integration. |

### Discovery Mode

В `real`-режиме доступны три стратегии обнаружения закупок, управляемые `AI_CORP_TENDER_RESEARCH_EIS_DISCOVERY_MODE`:

| Strategy | Env value | Endpoint | Status |
|----------|-----------|----------|--------|
| Search | `search` | `int44.zakupki.gov.ru` (legacy `searchProcurements`) | ❌ `Connection reset by peer` — сервер блокирует |
| Registry numbers | `registry_numbers` (default) | `int.zakupki.gov.ru` (getDocsIP) | ✅ Работает, но требует seed-файла |
| GetDocsIP | `get_docs_ip` | `int.zakupki.gov.ru` (getDocsIP) | ✅ То же, что registry_numbers |

**Основной production-safe путь:** `registry_numbers` — загрузка по списку реестровых номеров через `getDocsByReestrNumber`.

### Проверка конфигурации

```bash
python -m src.tender_research.cli check-eis-config
```

Вывод:
- `eis_mode` — текущий режим
- `eis_discovery_mode` — текущая стратегия
- `endpoint` — URL getDocsIP
- `legacy_endpoint` — URL legacy search
- `token_present: true/false`
- `token_masked` — первые 4 + последние 4 символа токена
- `available_methods` — какие методы реально работают

### Загрузка по списку реестровых номеров

Seed-файл: `data/eis_seed/registry_numbers.txt` — один номер на строку, `#` для комментариев.

```bash
python -m src.tender_research.cli ingest-eis-registry-list \
  --file data/eis_seed/registry_numbers.txt \
  --limit 3
```

Для каждого номера вызывается `getDocsByReestrNumber`. Результаты:
- `saved` — успешно сохранено
- `no_data` — номер есть, но документов нет
- `connection_resets` — ошибка соединения
- `missing_token` — токен не настроен

### Ошибки EIS — классификация

Ошибки разделены по типам, чтобы connection reset не путать с missing token:

| Тип | Причина |
|-----|---------|
| `EisMissingTokenError` | Токен не найден или SOAP не настроен |
| `EisAuthFailedError` | 401/403/SOAP Fault |
| `EisConnectionResetError` | `[Errno 54] Connection reset by peer` — сервер сбросил соединение |
| `EisNoDataError` | getDocsIP вернул `no_data` — документов нет |
| `EisParseError` | Ошибка парсинга XML/SOAP-ответа |

### Prerequisites for `real` mode

The existing `ZAKUPKI_GOV_RU_SOAP_*` env vars must be configured (see `.env.example` lines 36–63, or `docs/product/zakupki_soap_integration.md`). At minimum:

```bash
export AI_CORP_ZAKUPKI_GOV_RU_SOAP_ENABLED=true
export AI_CORP_ZAKUPKI_GOV_RU_SOAP_TOKEN=<your-44fz-individual-person-token>
```

CLI автоматически загружает `.env` и `.env.local` через `python-dotenv`. Если токен лежит в `.env.local`, он будет найден.

### Architecture

```
EisTenderLoader (mode="demo"|"real", discovery_mode="registry_numbers")
├── demo  →  _get_demo_tenders() / _get_demo_documents()
└── real  →  RealEisLoader (src/tender_research/eis_real_loader.py)
              ├── fetch_by_registry_number()  →  getDocsByReestrNumber  (работает)
              ├── fetch_tenders()             →  searchProcurements     (legacy, connection reset)
              ├── fetch_tender_details()      →  getProcurementDetails  (legacy, connection reset)
              └── fetch_tender_documents()    →  listAttachments        (legacy, connection reset)
```

## How to Enable Web Search

По умолчанию `WEB_SEARCH_ENABLED=false`. Для включения:

```bash
export AI_CORP_WEB_SEARCH_ENABLED=true
# или добавить в .env
AI_CORP_WEB_SEARCH_ENABLED=true
```

## How to Run Batch

```bash
# Статистика
python -m src.tender_research.cli stats

# Загрузка закупок из ЕИС
python -m src.tender_research.cli ingest-eis --limit 5

# Полный цикл
python -m src.tender_research.cli research-batch --limit 3 --web-search

# Одна закупка
python -m src.tender_research.cli research-one 0373100000124000001

# Только запросы
python -m src.tender_research.cli build-queries <tender-uuid>

# Только поиск
python -m src.tender_research.cli web-search <tender-uuid>

# Только fetch страниц
python -m src.tender_research.cli fetch-pages <tender-uuid> --limit 10
```

## Env Variables

```
AI_CORP_ARVECTUM_DATA_DIR=./data
AI_CORP_TENDER_RESEARCH_ENABLED=true
AI_CORP_TENDER_RESEARCH_BATCH_LIMIT=10
AI_CORP_TENDER_RESEARCH_EIS_MODE=demo
AI_CORP_TENDER_RESEARCH_EIS_DISCOVERY_MODE=registry_numbers
AI_CORP_WEB_SEARCH_ENABLED=false
AI_CORP_WEB_SEARCH_PROVIDER=duckduckgo_html
AI_CORP_WEB_SEARCH_MAX_QUERIES_PER_TENDER=8
AI_CORP_WEB_SEARCH_MAX_RESULTS_PER_QUERY=10
AI_CORP_WEB_SEARCH_DELAY_SECONDS=3
AI_CORP_WEB_SEARCH_TIMEOUT_SECONDS=20
AI_CORP_WEB_FETCH_ENABLED=true
AI_CORP_WEB_FETCH_MAX_PAGES_PER_TENDER=20
AI_CORP_WEB_FETCH_DELAY_SECONDS=2
AI_CORP_WEB_FETCH_TIMEOUT_SECONDS=30
AI_CORP_WEB_FETCH_MAX_FILE_SIZE_MB=25
AI_CORP_WEB_USE_PLAYWRIGHT=false
AI_CORP_WEB_SAVE_SCREENSHOTS=false
AI_CORP_WEB_DENY_DOMAINS=
AI_CORP_WEB_ALLOW_DOMAINS=
AI_CORP_DOCUMENT_DOWNLOAD_MAX_SIZE_MB=100
AI_CORP_DOCUMENT_EXTRACT_MAX_CHARS=2000000
```

## Limitations

1. **HTML-поиск нестабилен** — DuckDuckGo может блокировать частые запросы или менять HTML-структуру.
2. **Возможны блокировки/капчи** — requests-запросы к некоторым сайтам могут быть заблокированы.
3. **Playwright не является поисковиком** — он только открывает страницы, не индексирует.
4. **Нет LLM-анализа** — данные только собираются, не анализируются.
5. **Сканы без OCR** — PDF-сканы не распознаются.
6. **Внешние сайты сохраняются как raw data** — без обработки, фильтрации или категоризации.

## Next Steps (для локальной LLM/RAG)

1. Document chunking (разбивка текстов на чанки с overlap)
2. Embeddings (локально через sentence-transformers или llama.cpp)
3. Vector store (SQLite + sqlite-vec, Chroma, или FAISS)
4. RAG-запросы к накопленным данным
5. Risk extraction prompt
6. Typical customer requirements mining
7. Supplier text clustering
