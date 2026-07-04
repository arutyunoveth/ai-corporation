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
| `real` | Wraps `ZakupkiSoapClient` from the existing EIS SOAP integration. Makes real SOAP calls to `zakupki.gov.ru`. |

### Prerequisites for `real` mode

The existing `ZAKUPKI_GOV_RU_SOAP_*` env vars must be configured (see `.env.example` lines 36–63, or `docs/product/zakupki_soap_integration.md`). At minimum:

```bash
export AI_CORP_ZAKUPKI_GOV_RU_SOAP_ENABLED=true
export AI_CORP_ZAKUPKI_GOV_RU_SOAP_TOKEN=<your-44fz-individual-person-token>
```

Then run with `--eis-mode real`:

```bash
python -m src.tender_research.cli research-batch --limit 3 --eis-mode real
```

Without a valid token, `real` mode returns empty results and logs warnings.

### Architecture

```
EisTenderLoader (mode="demo"|"real")
├── demo  →  _get_demo_tenders() / _get_demo_documents()
└── real  →  RealEisLoader (src/tender_research/eis_real_loader.py)
              └── ZakupkiSoapClient (src/modules/tender_operator_agent_demo/)
```

`RealEisLoader` maps:
- `fetch_tenders()` → `ZakupkiSoapClient.search_procurements()` → `EisTenderRaw`
- `fetch_tender_details()` → `ZakupkiSoapClient.get_procurement_details()` → `EisTenderRaw` + `EisDocumentRaw`
- `fetch_tender_documents()` → `ZakupkiSoapClient.list_attachments()` → `EisDocumentRaw`

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
