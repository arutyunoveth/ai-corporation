# Tender-app Reuse Audit

## Где искали

Заданный путь `/Users/master/tender-app` на этой машине не содержит проект.

Проверенные альтернативы:

- `/Users/master/Documents/tender-app` — проект не найден.
- `/Users/master/Projects/tender-app` — проект не найден.
- `/Users/master/Documents/Opencode/tender-app` — фактический локальный черновик найден.

Аудит ниже относится к `/Users/master/Documents/Opencode/tender-app`.

## Что найдено

Старый `tender-app` — отдельный Python/FastAPI MVP для закупок малого объёма:

- CLI для demo/production сценариев;
- dashboard;
- SQLite/PostgreSQL контур;
- коннекторы `mos_portal` и `eat`;
- real-network режимы;
- browser fallback через Playwright как опциональная зависимость;
- Excel export;
- правила каталога, matching/scoring, risk/economics logic;
- install-скрипты для Mac mini.

## Стек

- Python `>=3.11`;
- FastAPI / Uvicorn;
- SQLAlchemy / Alembic;
- Pydantic;
- requests;
- openpyxl;
- python-dotenv;
- Typer CLI;
- APScheduler;
- optional Playwright.

## Функции поиска

В старом проекте есть read-only идеи, полезные как reference:

- `app/connectors/mos_portal/api_client.py` — попытки публичного API поиска закупок `zakupki.mos.ru`;
- `app/connectors/eat/api_client.py` — аналогичный API-probing контур для `eat`;
- нормализация карточек закупок в единый внутренний формат;
- warnings/errors для неустойчивых публичных endpoint'ов;
- `requests.Session`, User-Agent, таймауты, proxy routing.

## Функции скачивания документации

Найден `install/mos_portal_extract_attachments.py`.

Он показывает полезные паттерны:

- получать список файлов по публичному идентификатору закупки;
- фильтровать вложения по имени;
- нормализовать имена файлов;
- вести manifest и reasons;
- не считать скачивание успешным, если получена HTML-страница вместо файла.

Этот код не перенесён как есть, потому что он привязан к `zakupki.mos.ru`, real-network состоянию сайта и старой архитектуре.

## Зависимости

Потенциально переносимые идеи не требуют монолитного переноса зависимостей.

В `ai-corporation` уже использованы существующие зависимости и стандартная библиотека:

- FastAPI/Pydantic для API contracts;
- `urllib` для безопасного read-only SOAP/attachment HTTP;
- `xml.etree.ElementTree` с защитой от DTD/ENTITY;
- текущий upload/analyze pipeline;
- текущий XLSX parser на `openpyxl`.

## Есть ли секреты/токены

В старом проекте есть `.env`/production-related настройки и install/run scripts, поэтому его нельзя копировать целиком.

В `ai-corporation` секреты не переносились. Токен ЕИС хранится только локально у пользователя в `.env.local` и не должен попадать в код, docs с реальным значением, README, тесты или git history.

## Что переиспользовано

Переиспользованы только архитектурные идеи:

- read-only procurement discovery перед document intake;
- единый нормализованный procurement result;
- attachments manifest;
- причины пропуска документов;
- manual upload fallback;
- downstream reuse существующего Upload & Analyze pipeline.

Код старого проекта не импортирован монолитом.

## Что не перенесено

Не перенесены:

- browser fallback / Playwright;
- авторизация, cookies, storage state;
- production install scripts;
- dashboard/auth infrastructure;
- scheduler/monitoring;
- semi-automatic price search;
- real-network scraping paths;
- `mos_portal`/`eat` коннекторы как активные источники.

Причина: эти части требуют отдельного security/legal/product review и не соответствуют текущему controlled demo/pilot scope.

## Почему выбран SOAP-коннектор

Для текущего batch выбран `zakupki_gov_ru_soap`, потому что он лучше соответствует безопасному demo/pilot контуру:

- источник конфигурируется через env;
- включается только при `ZAKUPKI_GOV_RU_SOAP_ENABLED=1` и наличии токена;
- не требует логина в личный кабинет;
- не использует cookies;
- не обходит captcha;
- не использует browser automation;
- работает как read-only получение публичной информации и документации.

`demo_local` остаётся стабильным offline-safe источником по умолчанию.

## Риски и ограничения

- Реальные SOAP mappings могут потребовать уточнения после проверки фактических ответов ЕИС.
- Live SOAP тесты не должны быть обязательными в CI и запускаются только вручную.
- Скачивание вложений ограничено allowlist-форматами, доменами, размером и количеством файлов.
- Если документация недоступна, run получает `docs_required`, а оператор вручную загружает документы.
- Система не подаёт заявки, не подписывает документы, не отправляет email и не выполняет действия на площадках.
