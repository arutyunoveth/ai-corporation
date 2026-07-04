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

Seed-файл: `data/eis_seed/registry_numbers.txt` — один номер на строку, `#` для комментариев. Поддерживается также JSON-формат (список или `{"items": [...]}`).

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

## Registry Number Discovery Architecture

`src/tender_research/registry_discovery.py` — `RegistryNumberDiscovery` с честным разделением источников.

### Source types

| Source | Type | Description | Empty query | Pagination | Date range | Status |
|--------|------|-------------|-------------|------------|------------|--------|
| `external_public_44fz` | `external_public` | Парсинг zakupki.gov через `Public44FzSearchProvider` | ✅ — все закупки за период | ✅ 30 карточек (max 100) | ✅ | Честно пишет blocked/timeout/bad_gateway |
| `local_db` | `local_db` | Поиск по локальной БД | ✅ | — | ✅ | Не считается external discovery |
| `seed_file` | `seed_file` | Чтение из файла (.txt или .json) | — | — | — | Простой список номеров |
| `demo` | `demo` | 3 демо-закупки | ✅ | — | ✅ | Только для тестирования |
| `backend_search_real` | `unavailable` | Реальный backend search | — | — | — | Пока не реализован |
| `auto` | (fallback) | external_public → seed_file → demo | ✅ | ✅ | ✅ | Не маскирует блокировку |

### DiscoveryResult metadata

```python
result.selected_source       # "external_public_44fz"
result.selected_source_type  # "external_public_44fz"
result.pages_read            # 3
result.page_size             # 30
result.discovered_count      # 42
result.network_status        # "blocked" / "timeout" / "bad_gateway"
result.is_demo               # False
result.warnings              # [...]
result.errors                # [...]
```

### Auto fallback

`auto` пробует:
1. `external_public_44fz` (если заблокирован — не маскирует под empty)
2. `seed_file` (если есть)
3. `demo` (только если `allow_demo_discovery=true`)

Если сеть заблокирована, Mac mini не увидит "0 закупок", а увидит:
```
network_status: bad_gateway
warning: external_public_44fz is bad_gateway: Tunnel connection failed: 502 Bad Gateway
```

## Public44FzSearchProvider (общий provider)

`src/tender_research/providers/public_44fz_search.py` — единый provider для публичного поиска 44-ФЗ.

Используется:
- `RegistryNumberDiscovery` — через `external_public_44fz` source
- `src/modules/tender_operator_agent_demo/` — через re-экспорт

```python
from src.tender_research.providers.public_44fz_search import Public44FzSearchProvider

provider = Public44FzSearchProvider(
    timeout_seconds=15,
    delay_seconds=3.0,  # между страницами
    bypass_proxy=True,  # игнорировать system proxy
)

# Поиск с пустым query = все закупки за период
result = provider.search(query=None, date_from=..., date_to=..., page=1, page_size=30)

# Пагинация
pages = provider.search_pages(query=None, max_pages=5, page_size=30)

# Извлечение номеров
numbers = provider.extract_registry_numbers(pages)
```

### Поведение пустого query

- `query=None` или `query=""` — без ключевых слов, все закупки за период
- Используется фильтр даты
- Если даты не переданы — default последние 3 дня
- `page_size` по умолчанию 30, максимум 100

### Network status

Источник честно сообщает о состоянии сети:

| Status | Meaning |
|--------|---------|
| `success` | HTML получен и распарсен |
| `blocked` | captcha, connection reset, 403 |
| `timeout` | Request timed out |
| `bad_gateway` | 502/503 от прокси |
| `parse_error` | HTML получен, но не распарсен |
| `empty` | Нет карточек на странице (пустой результат) |

## CLI Commands

### discover-registry-numbers

```bash
# Auto (fallback chain)
python -m src.tender_research.cli discover-registry-numbers \
  --source auto --days-back 3 --limit 90 --page-size 30

# External public 44-FZ (zakupki.gov.ru scraping)
python -m src.tender_research.cli discover-registry-numbers \
  --source external_public_44fz --days-back 3 --limit 90 --page-size 30

# Seed file (.txt or .json)
python -m src.tender_research.cli discover-registry-numbers \
  --source seed_file --limit 10

# Local DB
python -m src.tender_research.cli discover-registry-numbers \
  --source local_db --days-back 30 --limit 10

# Save output
python -m src.tender_research.cli discover-registry-numbers \
  --source external_public_44fz --days-back 3 --limit 30 \
  --output data/eis_seed/registry_numbers_auto.txt
```

Вывод:
```
selected_source: external_public_44fz
selected_source_type: external_public_44fz
is_demo: False
discovered_count: 15
pages_read: 1
page_size: 30
network_status: success
total_numbers: 15
  0373200008225000001
  0373200008225000002
  ...
```

### research-discovered

```bash
python -m src.tender_research.cli research-discovered \
  --source seed_file \
  --seed-file data/eis_seed/registry_numbers.txt \
  --limit 10 \
  --web-search \
  --fetch-pages
```

### collect-registry-numbers (external collector)

Запускать на машине **с доступом к zakupki.gov.ru**:

```bash
# На машине с РФ-доступом
python -m src.tender_research.cli collect-registry-numbers \
  --days-back 3 \
  --limit 300 \
  --page-size 30 \
  --output data/eis_seed/registry_numbers_collected.json
```

Форматы:
- `.txt` — только номера, по одному на строку
- `.json` — полные объекты с title, customer_name, publication_date

Скопировать на Mac mini:
```bash
rsync -av data/eis_seed/registry_numbers_collected.json \
  <macmini>:/path/to/ai-corporation/data/eis_seed/
```

На Mac mini — загрузка через SOAP:
```bash
# Через ingest-collected
python -m src.tender_research.cli ingest-collected-registry-numbers \
  --file data/eis_seed/registry_numbers_collected.json \
  --limit 30

# Или через research-discovered с JSON seed
python -m src.tender_research.cli research-discovered \
  --source seed_file \
  --seed-file data/eis_seed/registry_numbers_collected.json \
  --limit 30
```

### ingest-collected-registry-numbers

```bash
python -m src.tender_research.cli ingest-collected-registry-numbers \
  --file data/eis_seed/registry_numbers_collected.json \
  --limit 30
```

### Network diagnosis: zakupki.gov.ru accessibility

Текущая сетевая среда (MacBook Air + Mac mini, оба за корпоративным прокси):

| Ресурс | Доступ | Задержка | Причина |
|--------|--------|----------|---------|
| `zakupki.gov.ru` (443) | ❌ | 0.03s (RST) | Санкционная/сетевая блокировка |
| `int.zakupki.gov.ru` (443) | ❌ | 0.06s (RST) | Та же блокировка |
| `int.zakupki.gov.ru/eis-integration/services/getDocsIP` (SOAP) | ✅ | ~6s | Аутентифицированный доступ через токен |
| `tunnel-proxy 127.0.0.1:8080` через `196.18.15.245:8000` | ❌ 502 | — | Прокси не может достучаться до zakupki.gov.ru |
| Bypass proxy (direct) | ❌ timeout | 5-10s | Нет маршрута к РФ |

**Вывод:** `external_public_44fz` не работает из этой сети в принципе.
Единственный рабочий путь — `seed_file` (с номерами от внешнего collector) → `getDocsByReestrNumber`.

### Реальный seed fallback

Если `auto` не нашёл реальные номера, добавьте их вручную в seed-файл:

```bash
# Посмотреть формат demo seed
cat data/eis_seed/registry_numbers.txt

# Создать свой seed-файл
echo "0373100000124000001" > data/eis_seed/registry_numbers_real.txt

# Использовать
python -m src.tender_research.cli research-discovered \
  --source seed_file \
  --seed-file data/eis_seed/registry_numbers_real.txt \
  --limit 10 \
  --web-search \
  --fetch-pages
```

Как получить реальные номера закупок:
1. Открыть https://zakupki.gov.ru в браузере (если есть доступ)
2. Найти интересующие закупки
3. Скопировать `regNumber=xxxxxxxxxxxxxxxxxxx` из URL
4. Положить в seed-файл

### Collector-требования для MacBook (если есть доступ к РФ)

Если MacBook имеет доступ к zakupki.gov.ru (например, через российский VPN), выполнить:

```bash
# На MacBook (не требует SOAP-токена)
python -m src.tender_research.cli collect-registry-numbers \
  --days-back 7 --limit 50 --page-size 30 \
  --output data/eis_seed/registry_numbers_collected.json

# Скопировать на Mac mini
rsync -av data/eis_seed/registry_numbers_collected.json \
  <macmini>:/path/to/ai-corporation/data/eis_seed/

# На Mac mini — загрузка и исследование
python -m src.tender_research.cli research-discovered \
  --source seed_file \
  --seed-file data/eis_seed/registry_numbers_collected.json \
  --limit 10 \
  --web-search \
  --fetch-pages
```

### Document Deduplication (document_identity_hash)

**Проблема:** до скачивания документа `sha256 = NULL`, поэтому дедупликация только по `tender_id + sha256` не работает. Повторный вызов `upsert_document` с одинаковыми данными создаёт дубли.

**Решение:** добавлен `document_identity_hash` — стабильный логический идентификатор документа, вычисляемый без скачивания:

| Priority | Условие | identity_source | identity_value |
|----------|---------|-----------------|----------------|
| 1 | `source_document_id` есть | `source_document_id` | нормализованный source_document_id |
| 2 | `file_url` есть | `file_url` | URL без utm/ref/tracking params |
| 3 | `file_name` есть | `file_name` | file_name + size_bytes + content_type |
| 4 | `raw_meta` есть | `raw_meta` | стабильный JSON hash |

`document_identity_hash = sha256(tender_id + "|" + identity_source + "|" + identity_value)`

**Как работает upsert:**
1. Ищем по `tender_id + document_identity_hash` (если identity доступен)
2. Если не нашли — ищем по `tender_id + sha256` (backward compatibility)
3. Если нашли — обновляем существующую строку (включая sha256 после скачивания)
4. Если не нашли — создаём новую

**Unique constraint:** `ux_procurement_tender_documents_doc_identity` (partial index, `WHERE document_identity_hash IS NOT NULL`).

**Дубликаты больше не создаются** при повторном запуске ингеста с одинаковыми документами.

### Prerequisites for `real` mode

The existing `ZAKUPKI_GOV_RU_SOAP_*` env vars must be configured (see `.env.example` lines 36–63, or `docs/product/zakupki_soap_integration.md`). At minimum:

```bash
export AI_CORP_ZAKUPKI_GOV_RU_SOAP_ENABLED=true
export AI_CORP_ZAKUPKI_GOV_RU_SOAP_TOKEN=<your-44fz-individual-person-token>
```

CLI автоматически загружает `.env` и `.env.local` через `python-dotenv`. Если токен лежит в `.env.local`, он будет найден.

### Architecture

```
Public44FzSearchProvider (shared, src/tender_research/providers/public_44fz_search.py)
├── search(query, date_from, date_to, page, page_size)
├── search_pages(max_pages)  ← пагинация по 30
├── extract_registry_numbers(pages)
└── _fetch_page(url)  ← urllib, bypass proxy, SSL verify disabled

RegistryNumberDiscovery (src/tender_research/registry_discovery.py)
├── _external_public_44fz()  → Public44FzSearchProvider
├── _seed_file()             → .txt / .json
├── _local_db()              → DB query
├── _demo_discover()         → 3 demo tenders
└── _auto_discover()         → fallback chain

EisTenderLoader (mode="demo"|"real", discovery_mode="registry_numbers")
├── demo  →  _get_demo_tenders() / _get_demo_documents()
└── real  →  RealEisLoader (src/tender_research/eis_real_loader.py)
              ├── fetch_by_registry_number()  →  getDocsByReestrNumber  (работает)
              ├── fetch_tenders()             →  searchProcurements     (legacy, dead)
              ├── fetch_tender_details()      →  getProcurementDetails  (legacy, dead)
              └── fetch_tender_documents()    →  listAttachments        (legacy, dead)
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
AI_CORP_REGISTRY_DISCOVERY_SOURCE=auto
AI_CORP_REGISTRY_DISCOVERY_DAYS_BACK=3
AI_CORP_REGISTRY_DISCOVERY_LIMIT=10
AI_CORP_PUBLIC_SEARCH_ENABLED=true
AI_CORP_PUBLIC_SEARCH_DELAY_SECONDS=3
AI_CORP_PUBLIC_SEARCH_TIMEOUT_SECONDS=30
AI_CORP_PUBLIC_SEARCH_BYPASS_PROXY=false
AI_CORP_PUBLIC_SEARCH_PAGE_SIZE=30
AI_CORP_TENDER_RESEARCH_ALLOW_DEMO_DISCOVERY=true
AI_CORP_TENDER_RESEARCH_EIS_SEED_FILE=data/eis_seed/registry_numbers.txt
```

## Limitations

1. **HTML-поиск нестабилен** — DuckDuckGo может блокировать частые запросы или менять HTML-структуру.
2. **Возможны блокировки/капчи** — requests-запросы к некоторым сайтам могут быть заблокированы.
3. **Playwright не является поисковиком** — он только открывает страницы, не индексирует.
4. **Нет LLM-анализа** — данные только собираются, не анализируются.
5. **Сканы без OCR** — PDF-сканы не распознаются.
6. **Внешние сайты сохраняются как raw data** — без обработки, фильтрации или категоризации.
7. **external_public_44fz блокирован на Mac mini** — через корпоративный прокси `502 Bad Gateway`, напрямую `Read timed out` (санкционные блокировки). Bypass через `AI_CORP_TENDER_RESEARCH_PUBLIC_SEARCH_BYPASS_PROXY=true` убирает прокси, но не даёт доступ к `zakupki.gov.ru`.
8. **demo-режим** — возвращает только 3 демо-закупки.
9. **DB-level UNIQUE на document_identity_hash** — частичный индекс (`WHERE IS NOT NULL`). При миграции с существующими данными может потребоваться ручная дедупликация перед включением полного UNIQUE.
10. **backend_search_real не реализован** — нет внешнего backend search endpoint. Discovery через реальный backend search пока невозможен.

## Next Steps (для локальной LLM/RAG)

1. Document chunking (разбивка текстов на чанки с overlap)
2. Embeddings (локально через sentence-transformers или llama.cpp)
3. Vector store (SQLite + sqlite-vec, Chroma, или FAISS)
4. RAG-запросы к накопленным данным
5. Risk extraction prompt
6. Typical customer requirements mining
7. Supplier text clustering

## TODO

- [ ] **DB-level UNIQUE constraint** на `(tender_id, document_identity_hash)` без условия `WHERE NOT NULL`. Требует: (a) backfill всех существующих строк, (b) дедупликации дублей, (c) миграции с переходом на полный UNIQUE.
- [ ] **Discovery cache** — не переоткрывать уже обработанные registry numbers.
- [ ] **Параллельная загрузка** документов для одного тендера (сейчас последовательная).
- [ ] **backend_search_real** — реализовать, когда появится рабочий backend search endpoint.
