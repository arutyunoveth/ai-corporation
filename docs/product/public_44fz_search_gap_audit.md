# Public 44-FZ Search Gap Audit

Дата аудита: 2026-06-24

Контекст: audit current search/discovery layer перед добавлением публичного поиска 44-ФЗ с handoff в live getDocsIP.

## Что уже есть

### demo_local (offline-safe)

- `src/modules/tender_operator_agent_demo/procurement_sources.py` — 6 синтетических закупок с документацией.
- `src/modules/tender_operator_agent_demo/procurement_discovery.py` — `search_procurements()` фильтрует `demo_local` по `query`, `source`, `region`, `date`, `price`.
- `build_public_search_url()` — формирует ссылку поиска ЕИС для 44-ФЗ и 223-ФЗ, но только с `searchString`, `region`, `publishDateFrom`, `publishDateTo`.
- UI вкладка "Найти закупку" работает: поиск по `demo_local`, показ карточек, кнопка "Скачать документацию и анализировать".

### public_eis_html_44fz / public_eis_html_223fz (public HTML fallback)

- Источники объявлены в `list_procurement_sources()` и `get_procurement_source_descriptors()`.
- В UI при выборе `public_eis_html_44fz` формируется ссылка поиска через `GET /api/demo/tender-agent/procurement/public-search-url`.
- Показывается кнопка "Открыть поиск ЕИС" в новой вкладке.
- **Нет parser** — HTML не анализируется, карточки закупок не извлекаются.
- **Нет handoff** — после ручного выбора закупки пользователь должен сам скопировать номер и перейти на вкладку "Получить документацию по номеру".
- **Нет единого one-click flow** от поиска до анализа.

### zakupki_gov_ru_getdocs_ip (live intake)

- `getDocsByReestrNumber` SOAP-метод работает.
- Python-клиент ходит напрямую (direct_for_eis), без proxy.
- `archiveUrl` получается, архив скачивается, документы распаковываются.
- `create_run_from_eis_docs_archive()` создаёт run, запускает анализ.
- Есть retry для `archive_not_ready`, fallback на `manual_upload_required`.
- Полные event log, polling, report.

## Gap-ы

### 1. Нет отдельного URL builder для 44-ФЗ с полными параметрами

`build_public_search_url()` не поддерживает:
- `priceFrom` / `priceTo`;
- `max_results` / `recordsPerPage`;
- валидацию хоста и схемы;
- нормализацию параметров.

### 2. Нет HTML parser для публичной выдачи ЕИС

- HTML не загружается, не классифицируется, не парсится.
- Нет определения `captcha_or_blocked`, `js_heavy`, `empty_results`, `unsupported_layout`.
- Нет извлечения `reestrNumber` из карточки или URL.

### 3. Нет handoff endpoint "search result → getDocsIP"

- После выбора закупки из результатов поиска нет единого endpoint, который:
  - принимает `reestr_number`;
  - вызывает getDocsIP;
  - скачивает архив;
  - создаёт run;
  - запускает анализ.
- Пользователь должен вручную копировать номер между вкладками.

### 4. UI не показывает one-click flow

- В карточке найденной закупки нет кнопки "Получить документацию и анализировать" для `public_eis_html` source.
- Нет состояния `manual_open_required` с полем для вставки ссылки/номера.
- Нет блока "Закупка найдена через публичный поиск ЕИС" в report.

### 5. Нет тестов для public 44-ФЗ search и parser

- `test_tender_operator_agent_procurement_ui.py` тестирует только `demo_local` и `public_eis_html_44fz` как fallback.
- Нет тестов URL builder, parser, handoff flow.

## Вывод

Текущий public HTML fallback — это только ссылка, а не поиск. Чтобы сделать "найти закупку → карточка → getDocsIP" в one click, нужно:
1. Выделить `public_44fz_search.py` с URL builder + validation.
2. Создать `public_44fz_parser.py` с лёгким parser + честным fallback.
3. Добавить `POST /api/demo/tender-agent/runs/from-search-result`.
4. Обновить UI для one-click flow.
5. Покрыть тестами.
