# Tender-app Reuse Audit

## Контекст

В задаче был указан путь:

`/Users/master/tender-app`

Фактически локальный черновик старого проекта найден по пути:

`/Users/master/Documents/Opencode/tender-app`

Аудит выполнялся по этому фактическому пути.

## Что найдено

Старый `tender-app` — отдельный Python/FastAPI-проект уровня локального MVP.

Найдены:

- `README.md` с demo и production сценариями;
- `pyproject.toml` с зависимостями `fastapi`, `requests`, `openpyxl`, опционально `playwright`;
- коннекторы для `mos_portal` и `eat`;
- browser fallback logic;
- публичные HTTP/API вызовы;
- CLI и dashboard;
- real-network и browser-oriented сценарии;
- `.env` и сетевые настройки, которые нельзя переносить вслепую.

## Что можно переиспользовать

Безопасно переиспользуемые идеи:

- read-only procurement discovery как отдельный слой перед document intake;
- нормализацию procurement cards в единый компактный результат;
- идею аккуратного отбора только релевантных закупочных документов;
- идею manifest для вложений и причин, почему документ не был получен.

Из конкретного кода полезны как reference-only:

- `install/mos_portal_extract_attachments.py`
  - показывает безопасный паттерн `requests.Session(trust_env=False)`;
  - показывает фильтрацию имён файлов;
  - показывает жёсткий allowlist-подход для документов.
- `app/connectors/mos_portal/api_client.py`
  - показывает, что в старом проекте был read-only public API probing контур.
- `app/connectors/mos_portal/browser_fallback.py`
  - полезен только как индикатор того, где начинаются зоны риска и нестабильности.

## Что не перенесено

Сознательно не переносились:

- browser fallback через Playwright;
- авторизация и storage state;
- cookies / логины;
- real network pipeline;
- semi-automatic price search;
- dashboard/auth infrastructure;
- production/install scripts;
- любые обходные или нестабильные scraping paths.

Причины:

- не соответствует ограничениям demo/pilot режима;
- повышает риск ложных обещаний по автономии;
- требует отдельного security и legal review;
- плохо вписывается в текущий объём controlled internal console.

## Какие источники там были

По структуре старого проекта подтверждены как минимум:

- `mos_portal`
- `eat`

Также есть признаки реального сетевого режима, browser doctor и production сценариев, что выводит этот контур за рамки safe demo-by-default.

## Есть ли скачивание документации

Да, в старом проекте найден скрипт:

`install/mos_portal_extract_attachments.py`

Он:

- вызывает публичные `zakupki.mos.ru` endpoint'ы;
- получает список файлов по `auctionId`;
- скачивает вложения;
- фильтрует документы по имени и извлекаемости текста;
- пишет manifest/reasons/examples.

Это полезно как reference для будущего audited read-only connector, но не было перенесено “как есть”.

## Основные риски старого проекта

- рядом присутствуют `.env` и production settings;
- есть browser automation и real-network логика;
- есть сценарии, завязанные на внешний сайт и его текущее состояние;
- есть storage state / auth-related paths;
- есть operational assumptions про российский IP и proxy/no_proxy.

Поэтому прямой перенос старого проекта как модуля в `ai-corporation` признан нежелательным.

## Что было перенесено в этот спринт

В `ai-corporation` перенесён не монолит, а минимальный безопасный слой:

- procurement discovery tab в `Tender Operator Agent Demo`;
- offline-safe `demo_local` source;
- procurement intake -> создание run;
- procurement metadata storage;
- attachments manifest;
- events log;
- честный manual upload fallback;
- reuse существующего upload/analyze pipeline downstream.

## Минимальный безопасный перенос

Решение этого спринта:

- `demo_local` включён по умолчанию;
- `mos_portal_public_api` отражён только как `disabled / experimental` источник;
- UI честно показывает, что real source пока не активирован;
- внешний read-only connector отложен до отдельного сетевого и продуктового аудита.

## Рекомендация

Следующим шагом можно делать только один audited real source connector:

- без логина;
- без captcha bypass;
- без browser automation;
- с таймаутами;
- с allowlist доменов;
- с ограничением размера и количества файлов;
- с обязательным fallback в `manual_upload_required`.
