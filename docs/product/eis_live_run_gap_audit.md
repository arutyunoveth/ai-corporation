# EIS Live Archive To Run Gap Audit

Дата аудита: 2026-06-23

Контекст:

- live `getDocsIP` для токена физлица уже работает;
- Python-клиент ходит к ЕИС напрямую, минуя системный proxy;
- `archiveUrl` получается и архив скачивается;
- run из `getDocsIP` уже создаётся в demo-модуле;
- полный `pytest` на момент аудита был зелёным.

## Что уже реализовано

### Live SOAP / archive intake

- `src/modules/tender_operator_agent_demo/zakupki_soap_client.py`
  - вызывает `getDocsByReestrNumber`, `getDocsByOrgRegion`, `getNsi`;
  - использует direct/no-proxy transport для ЕИС;
  - получает `archiveUrl`;
  - скачивает архив даже если URL не заканчивается на `.zip`;
  - ограничивает хосты allowlist-ом `zakupki.gov.ru`.

### Create run from EIS archive

- `src/modules/tender_operator_agent_demo/procurement_intake_service.py`
  - endpoint already creates run from `getDocsIP`;
  - архив скачивается;
  - архив безопасно распаковывается;
  - файлы попадают в локальный run storage;
  - metadata и events already write basic procurement/getDocsIP context;
  - есть retry для случая `archive_not_ready`.

### Existing run/analyze/report UI

- `src/modules/tender_operator_agent_demo/router.py`
  - уже есть `POST /api/demo/tender-agent/runs/from-eis-docs-archive`;
  - уже есть `POST /api/demo/tender-agent/runs/{run_id}/analyze`;
  - уже есть run page и report page.

- `src/modules/tender_operator_agent_demo/ui.py`
  - already has tab `Получить документацию по номеру`;
  - already submits `reestr_number` to `from-eis-docs-archive`;
  - already opens created run and triggers analysis automatically;
  - already shows generic procurement block and static event list.

- `src/modules/tender_operator_agent_demo/upload_service.py`
  - existing analyzer can process procurement-created runs;
  - report already includes procurement context at a generic level;
  - pipeline already switches to procurement-aware first step when `procurement_source` exists.

## What the current endpoint already does

Проверка по текущему коду:

- получает `archiveUrl`: да;
- скачивает архив: да;
- распаковывает архив: да;
- создаёт run: да;
- запускает анализ: да, но только косвенно через UI follow-up call, не как единый endpoint flag;
- показывает результат на run page: частично да;
- пишет events: да, но события пока общие и не полностью EIS-specific;
- добавляет блок в report: частично, только через generic procurement context.

## Основные gap-и

### 1. Endpoint contract ещё не доведён до полноценного live UI flow

Текущий `POST /api/demo/tender-agent/runs/from-eis-docs-archive`:

- не принимает `method`;
- не принимает `analyze_after_download`;
- возвращает generic `ProcurementRunResponse`, а не EIS-specific result payload;
- не возвращает явно:
  - `archive_url_present`;
  - `archive_downloaded`;
  - `documents_extracted_count`;
  - `analysis_status`;
  - sanitized archive summary.

### 2. Run storage structure ещё не полностью совпадает с целевым live-контуром

Сейчас:

- архив кладётся в `input/documentation-archive.zip`;
- extracted files пишутся в `input/`;
- procurement metadata пишется в generic files.

Не хватает:

- явного `input/extracted/`;
- отдельного `procurement/eis_getdocs_metadata.json`;
- отдельного `procurement/archive_manifest.json`;
- явного хранения sanitized archive summary вместо полного archive ticket URL.

### 3. UI вкладка `Получить документацию по номеру` ещё слишком тонкая

Сейчас:

- есть только `reestr_number`, `law`, `subsystem_type`;
- нет чекбоксов:
  - `Скачать архив`;
  - `Запустить анализ после скачивания`;
- нет явного результата по шагам:
  - SOAP status;
  - archiveUrl status;
  - archive download status;
  - extracted files count;
  - run link;
  - report link;
  - button `Запустить анализ`.

### 4. Run page не показывает полноценный EIS source block

Сейчас на run page есть generic procurement block.

Не хватает явных EIS полей:

- источник: `ЕИС getDocsIP`;
- `soap_method`;
- `refId`;
- `archive_url_present`;
- `archive_downloaded`;
- `archive_download_status`;
- `documents_extracted_count`;
- sanitized `host/path` summary вместо полного archive URL.

### 5. Analysis handoff работает, но не оформлен как отдельный EIS scenario

Сейчас анализ procurement-created runs уже проходит через existing upload/analyze pipeline.

Не хватает:

- явной функции/сценария `analyze_eis_archive_run(run_id)`;
- отдельной маркировки, что документы получены через ЕИС;
- controlled handling для:
  - XML-only archive;
  - слишком малого набора файлов;
  - incomplete extraction.

### 6. Report пока не содержит отдельный EIS source section

Сейчас procurement context уже используется в report generation, но не выделен как самостоятельный блок `Документы получены через ЕИС`.

Не хватает:

- `reestrNumber`;
- `soap_method`;
- `refId`;
- archive status;
- extracted files count;
- limitations specific to EIS intake;
- manual checks specific to EIS archive flow.

### 7. Event model ещё не отражает live EIS steps полностью

Сейчас используются generic event types:

- `attachments_download_started`;
- `attachment_saved`;
- `attachments_download_completed`;
- `manual_upload_required`;
- `analysis_started`;
- `analysis_completed`.

Не хватает EIS-specific событий:

- `eis_getdocs_started`;
- `eis_archive_url_received`;
- `eis_archive_download_started`;
- `eis_archive_downloaded`;
- `eis_archive_not_ready`;
- `eis_archive_extracted`;
- `run_created_from_eis_archive`;
- `analysis_ready`.

### 8. Нет отдельного polling endpoint для customer-facing agent journal

Сейчас события приходят только внутри общего run payload.

Не хватает:

- `GET /api/demo/tender-agent/runs/{run_id}/events`;
- polling в UI каждые 2-3 секунды;
- отдельного safety filtering для token / archive ticket / absolute paths.

## Архитектурный вывод

Большая часть инфраструктуры уже есть и не требует переписывания:

- working live SOAP client;
- working archive download;
- working safe unzip;
- working run storage;
- working analyzer;
- working report renderer;
- working run page.

Поэтому оптимальный путь:

1. не писать новый параллельный контур;
2. расширить текущий `from-eis-docs-archive`;
3. добавить EIS-specific metadata/events/report sections;
4. сделать UI richer и честнее;
5. добавить polling endpoint поверх уже существующего event log.

## Что переносить / не переносить в следующем шаге

Нужно делать:

- расширение существующего endpoint;
- расширение existing schemas/UI/renderers;
- reuse existing `analyze_uploaded_demo_run`;
- reuse existing event log storage.

Не нужно делать:

- отдельный новый frontend;
- отдельный новый analyzer;
- отдельный новый run storage outside current demo path;
- любые внешние действия beyond read-only EIS access.
