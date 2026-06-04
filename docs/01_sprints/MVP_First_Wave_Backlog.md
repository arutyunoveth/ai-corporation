# Backlog первой волны разработки ИИ-компании для тендерного бизнеса

## 1. Назначение документа

Этот документ переводит архитектуру в **рабочий backlog первой волны разработки**.

Он нужен, чтобы:
- управлять реализацией не по памяти, а по структуре;
- не терять ветки системы;
- видеть связь между бизнес-целями, модулями и сущностями;
- дать Codex / разработчику понятный build order;
- превратить MVP-ядро в **исполняемый план разработки**.

---

## 2. Правило чтения backlog

Структура backlog:

**Эпик → модуль → user stories → ключевые сущности → API/контракты → зависимости → Definition of Done**

Это значит:
- эпик отвечает на вопрос **какой кусок бизнеса строим**;
- модуль отвечает на вопрос **какой компонент системы нужен**;
- user stories отвечают на вопрос **что должен уметь модуль**;
- сущности отвечают на вопрос **какие formal records должны существовать**;
- API/контракты отвечают на вопрос **как модуль общается с другими**;
- зависимости отвечают на вопрос **что должно быть готово раньше**.

---

## 3. Границы первой волны

Первая волна заканчивается на цикле:

**тендер → анализ → supplier-side → экономика/риск → approval → заявка → подача → receipt → post-submission → outcome**

В первую волну **не входят**:
- полная execution-ветка после победы;
- расширенная governance-надстройка;
- полная observability-витрина owner-уровня.

---

# 4. BACKLOG ПЕРВОЙ ВОЛНЫ

# ЭПИК A. Platform skeleton

## Цель эпика
Построить базовый каркас системы, без которого нельзя двигать сделку по lifecycle.

## Модули эпика
- M-001 Deal Registry
- M-002 Status Model Engine
- M-003 Document Store
- M-004 Event Log & Decision Journal
- M-051 Workflow Orchestrator
- M-055 Integration Bus / Connectors Layer
- M-052 Notification Layer

---

## A1. M-001 Deal Registry

### User stories
1. Как система, я хочу создать canonical deal record при intake закупки.
2. Как система, я хочу хранить deal_id как единый ключ для всех downstream-модулей.
3. Как owner, я хочу иметь список всех сделок и их базовый lifecycle-контекст.

### Ключевые сущности
- `deal`
- `deal_identity`
- `deal_metadata`

### API / контракты
- `create_deal`
- `get_deal`
- `update_deal_metadata`
- `list_deals`

### Зависимости
- нет

### Definition of Done
- можно создать сделку;
- deal_id используется во всех downstream-контрактах;
- сделка доступна для статусного движка и workflow.

---

## A2. M-002 Status Model Engine

### User stories
1. Как система, я хочу переводить сделку только по allowed transitions.
2. Как owner, я хочу видеть текущий статус сделки и понимать, почему он изменился.
3. Как orchestrator, я хочу валидировать transitions before dispatch.

### Ключевые сущности
- `deal_status`
- `status_transition_rule`
- `status_history_entry`

### API / контракты
- `get_current_status`
- `validate_transition`
- `apply_transition`
- `get_status_history`

### Зависимости
- M-001

### Definition of Done
- статусы formalized;
- invalid transitions blocked;
- transition history preserved.

---

## A3. M-003 Document Store

### User stories
1. Как система, я хочу хранить документы и артефакты по сделке в едином месте.
2. Как downstream-модули, мы хотим ссылаться на documents by artifact_ref.
3. Как owner, я хочу, чтобы документы не были разбросаны по чатам и папкам.

### Ключевые сущности
- `document_artifact`
- `artifact_version`
- `artifact_link`

### API / контракты
- `store_artifact`
- `get_artifact`
- `version_artifact`
- `link_artifact_to_deal`

### Зависимости
- M-001

### Definition of Done
- каждый документ получает artifact_ref;
- версии поддерживаются;
- downstream-модули используют ref, а не raw file chaos.

---

## A4. M-004 Event Log & Decision Journal

### User stories
1. Как система, я хочу писать все критичные события в единый event log.
2. Как owner, я хочу понимать, почему было принято то или иное решение.
3. Как observability layer, я хочу читать audit trace from one source.

### Ключевые сущности
- `event_record`
- `decision_record`
- `audit_entry`

### API / контракты
- `append_event`
- `append_decision`
- `query_events`
- `query_decisions`

### Зависимости
- M-001
- M-002

### Definition of Done
- события и решения пишутся централизованно;
- есть query by deal/module/event type;
- лог пригоден для observability.

---

## A5. M-051 Workflow Orchestrator

### User stories
1. Как runtime core, я хочу маршрутизировать workflow events в правильные модули.
2. Как система, я хочу запускать dispatches только после valid transitions.
3. Как owner, я хочу иметь trace каждого workflow run.

### Ключевые сущности
- `workflow_run`
- `workflow_dispatch`

### API / контракты
- `route_workflow_event`
- `start_workflow_run`
- `retry_workflow_step`
- `apply_manual_override`

### Зависимости
- M-002
- M-004
- M-049
- M-050

### Definition of Done
- workflow runs formalized;
- dispatch trace preserved;
- retries and overrides explicit.

---

## A6. M-055 Integration Bus / Connectors Layer

### User stories
1. Как система, я хочу обращаться к email/portal/file connectors через единый слой.
2. Как module owner, я хочу не хардкодить интеграции в доменный код.
3. Как observability, я хочу видеть connector failures centrally.

### Ключевые сущности
- `integration_execution`
- `integration_retry_state`
- `connector_health`

### API / контракты
- `execute_connector_request`
- `process_inbound_connector_event`
- `retry_integration_execution`
- `check_connector_health`

### Зависимости
- platform runtime base

### Definition of Done
- integrations centralized;
- failures/retries visible;
- domain modules do not bypass bus.

---

## A7. M-052 Notification Layer

### User stories
1. Как система, я хочу доставлять critical alerts человеку.
2. Как owner, я хочу получать важное без notification spam.
3. Как modules, мы хотим делать notifications через единую policy-driven систему.

### Ключевые сущности
- `notification_record`

### API / контракты
- `create_notification`
- `send_notification`
- `suppress_notification`

### Зависимости
- M-048
- M-051

### Definition of Done
- urgency formalized;
- digest vs urgent separated;
- delivery failures visible.

---

# ЭПИК B. Intake & analysis

## Цель эпика
Превратить входящую закупку в структурированный объект анализа.

## Модули эпика
- M-008
- M-009
- M-010
- M-011
- M-012
- M-013
- M-014
- M-015

---

## B1. M-008 Tender Intake Pipeline

### User stories
1. Как система, я хочу intake new tender into canonical deal.
2. Как owner, я хочу быстро завести закупку в pipeline.
3. Как downstream, мы хотим получать intake-ready deal context.

### Ключевые сущности
- `tender_intake_record`

### API / контракты
- `ingest_tender_candidate`
- `normalize_tender_input`

### Зависимости
- M-001
- M-003
- M-051
- M-055

### Definition of Done
- новая закупка появляется в системе как deal;
- intake trace preserved.

---

## B2. M-009 Tender Screening Engine

### User stories
1. Как система, я хочу быстро отсеивать заведомо неподходящие сделки.
2. Как owner, я хочу не тратить supplier-side ресурсы на мусор.
3. Как scoring layer, я хочу получить candidate set после screening.

### Ключевые сущности
- `screening_result`

### API / контракты
- `screen_tender`
- `get_screening_result`

### Зависимости
- M-008
- M-002

### Definition of Done
- screening formalized;
- reject reasons explicit.

---

## B3. M-010 Priority Scoring Engine

### User stories
1. Как система, я хочу приоритизировать сделки после screening.
2. Как owner, я хочу видеть, за что мы беремся в первую очередь.
3. Как workflow, я хочу route only worth-doing candidates deeper.

### Ключевые сущности
- `priority_score_record`

### API / контракты
- `score_tender_priority`
- `get_priority_score`

### Зависимости
- M-009

### Definition of Done
- priority score exists;
- rationale visible.

---

## B4. M-011 Document Ingestion Layer

### User stories
1. Как система, я хочу нормализованно ingest тендерные документы.
2. Как analysis-модули, мы хотим получать document refs and parsed content basis.
3. Как owner, я хочу не работать с сырой файловой кашей.

### Ключевые сущности
- `document_ingestion_record`

### API / контракты
- `ingest_document_set`
- `extract_document_text_refs`

### Зависимости
- M-003
- M-008
- M-055

### Definition of Done
- doc set ingested;
- parsed refs available downstream.

---

## B5. M-012 Tender Summary Builder

### User stories
1. Как owner, я хочу короткую, но содержательную summary закупки.
2. Как система, я хочу summary as reusable downstream artifact.

### Ключевые сущности
- `tender_summary`

### API / контракты
- `build_tender_summary`

### Зависимости
- M-011

### Definition of Done
- summary generated;
- summary stored as formal artifact.

---

## B6. M-013 Compliance Matrix Builder

### User stories
1. Как система, я хочу formal matrix требований закупки.
2. Как supplier-side and risk-side, мы хотим structured requirement basis.

### Ключевые сущности
- `compliance_matrix`
- `compliance_row`

### API / контракты
- `build_compliance_matrix`

### Зависимости
- M-011

### Definition of Done
- matrix built;
- requirement rows traceable to sources.

---

## B7. M-014 Document Requirement Extractor

### User stories
1. Как bid-prep side, я хочу checklist обязательных документов.
2. Как completeness checker, я хочу formal requirements list.

### Ключевые сущности
- `document_requirement_set`
- `document_requirement_row`

### API / контракты
- `extract_document_requirements`

### Зависимости
- M-011

### Definition of Done
- requirement checklist exists;
- rows formalized.

---

## B8. M-015 Initial Tech Risk Flags

### User stories
1. Как owner, я хочу заранее видеть ambiguity и техриски.
2. Как risk contour, я хочу early flags before supplier work starts.

### Ключевые сущности
- `initial_risk_flag_set`

### API / контракты
- `build_initial_risk_flags`

### Зависимости
- M-011
- M-013

### Definition of Done
- early risk flags exist;
- critical ambiguity visible.

---

# ЭПИК C. Supplier engine

## Цель эпика
Построить supplier-side машину от shortlist до quote comparison.

## Модули эпика
- M-006
- M-016
- M-017
- M-018
- M-019
- M-020
- M-021

---

## C1. M-006 Supplier Registry

### User stories
1. Как система, я хочу единый реестр поставщиков.
2. Как supplier-side engine, я хочу переиспользовать supplier records between deals.

### Ключевые сущности
- `supplier_profile`

### API / контракты
- `create_supplier_profile`
- `get_supplier_profile`
- `update_supplier_profile`

### Зависимости
- core base

### Definition of Done
- supplier registry exists;
- supplier identity reusable.

---

## C2. M-016 Supplier Search

### User stories
1. Как система, я хочу находить shortlist поставщиков по deal requirements.
2. Как owner, я хочу видеть candidate suppliers, а не искать их вручную.

### Ключевые сущности
- `supplier_shortlist`
- `supplier_shortlist_row`

### API / контракты
- `search_suppliers`
- `build_supplier_shortlist`

### Зависимости
- M-006
- M-013
- M-015

### Definition of Done
- shortlist built;
- relevance trace preserved.

---

## C3. M-017 RFQ Generator

### User stories
1. Как система, я хочу генерировать RFQ batch по shortlist.
2. Как owner, я хочу, чтобы supplier-side outreach не делался вручную каждый раз.

### Ключевые сущности
- `rfq_batch`
- `rfq_record`

### API / контракты
- `build_rfq_batch`
- `generate_rfq_text`

### Зависимости
- M-014
- M-016

### Definition of Done
- RFQ batch generated;
- supplier-specific RFQs formalized.

---

## C4. M-018 Supplier Communication Tracker

### User stories
1. Как система, я хочу видеть supplier communication as threads.
2. Как owner, я хочу знать, кто ответил, кто молчит и где нужен follow-up.

### Ключевые сущности
- `supplier_communication_set`
- `communication_thread`
- `message_record`

### API / контракты
- `create_communication_set`
- `record_outbound_message`
- `record_inbound_message`
- `trigger_followup`

### Зависимости
- M-017
- M-055

### Definition of Done
- communication tracked formally;
- follow-up logic exists.

---

## C5. M-019 TKP Repository

### User stories
1. Как система, я хочу formal repository входящих ТКП.
2. Как downstream economics, я хочу работать не с письмами, а с quote objects.

### Ключевые сущности
- `quote_set`
- `quote_record`

### API / контракты
- `register_quote`
- `normalize_quote`
- `create_quote_revision`

### Зависимости
- M-018
- M-003

### Definition of Done
- quote records exist;
- versions supported.

---

## C6. M-020 Supplier Verification

### User stories
1. Как owner, я хочу понимать, что supplier — вменяемый контрагент.
2. Как comparison engine, я хочу учитывать supplier quality, а не только цену.

### Ключевые сущности
- `supplier_verification`
- `supplier_verification_flag`

### API / контракты
- `verify_supplier`
- `refresh_supplier_verification`

### Зависимости
- M-006
- M-019

### Definition of Done
- verification status formalized;
- flags explicit.

---

## C7. M-021 Quote Comparison Engine

### User stories
1. Как owner, я хочу сравнивать предложения не только по цене.
2. Как finance contour, я хочу structured comparison basis.

### Ключевые сущности
- `quote_comparison`
- `quote_comparison_row`

### API / контракты
- `build_quote_comparison`
- `refresh_quote_comparison`

### Зависимости
- M-019
- M-020
- M-013
- M-015

### Definition of Done
- comparison exists;
- recommendation explainable.

---

# ЭПИК D. Finance / Risk / Approval

## Цель эпика
Вывести сделку на formal go/no-go решение.

## Модули эпика
- M-022
- M-023
- M-024
- M-025
- M-026
- M-027
- M-028

---

## D1. M-022 Cost Model Engine
### User stories
- посчитать internal total cost;
- посчитать min viable bid line;
- видеть cost components explicitly.

### Сущности
- `cost_model`
- `cost_model_scenario`

### API
- `build_cost_model`
- `refresh_cost_model`

### Зависимости
- M-021

### DoD
- cost model built;
- scenarios supported.

---

## D2. M-023 Cash Gap Calculator
### User stories
- посчитать peak cash gap;
- увидеть duration of gap;
- увидеть liquidity risk.

### Сущности
- `cash_gap`
- `cash_gap_scenario`

### API
- `calculate_cash_gap`

### Зависимости
- M-022

### DoD
- gap amount + duration explicit.

---

## D3. M-024 Financing Strategy Engine
### User stories
- подобрать funding scenario;
- увидеть cost of financing;
- понять feasible vs infeasible path.

### Сущности
- `financing_strategy`
- `financing_strategy_scenario`

### API
- `build_financing_strategy`

### Зависимости
- M-022
- M-023

### DoD
- strategy recommendation exists;
- infeasible path supported.

---

## D4. M-025 Finance Memo Builder
### User stories
- собрать economics in one place;
- дать management-readable finance view.

### Сущности
- `finance_memo`
- `finance_memo_flag`

### API
- `build_finance_memo`

### Зависимости
- M-021
- M-022
- M-023
- M-024

### DoD
- finance memo exists;
- recommendation explicit.

---

## D5. M-026 Contract Risk Parser
### User stories
- разобрать payment / acceptance / penalty clauses;
- увидеть dangerous clauses before approval.

### Сущности
- `contract_risk`
- `contract_risk_flag`

### API
- `parse_contract_risk`

### Зависимости
- M-011

### DoD
- contract risk parsed;
- clause trace preserved.

---

## D6. M-027 Integrated Risk Memo Builder
### User stories
- собрать technical/supplier/finance/contract risks together;
- увидеть hard-stop candidates.

### Сущности
- `integrated_risk_memo`
- `integrated_risk_item`
- `integrated_risk_mitigation`

### API
- `build_integrated_risk_memo`

### Зависимости
- M-015
- M-020
- M-025
- M-026

### DoD
- unified risk memo built;
- category separation preserved.

---

## D7. M-028 CEO Approval Cockpit
### User stories
- принять formal decision;
- сохранить conditions и rationale;
- перевести сделку дальше only via explicit approval record.

### Сущности
- `ceo_approval`
- `ceo_approval_condition`

### API
- `record_ceo_decision`
- `reopen_approval`

### Зависимости
- M-025
- M-026
- M-027

### DoD
- approval formalized;
- no-go/go boundary explicit.

---

# ЭПИК E. Bid / Submission / Outcome

## Цель эпика
Довести одобренную сделку до controlled submission и formal outcome capture.

## Модули эпика
- M-029
- M-030
- M-031
- M-032
- M-033
- M-034
- M-035
- M-036
- M-037

---

## E1. M-029 Bid Document Collector
### User stories
- собрать документы заявки по checklist;
- видеть missing docs.

### Сущности
- `bid_document_collection_set`
- `bid_document_collection_row`

### API
- `build_bid_document_collection_set`

### Зависимости
- M-014
- M-028
- M-003

### DoD
- collection coverage explicit.

---

## E2. M-030 Bid Package Builder
### User stories
- собрать versioned package;
- получить manifest.

### Сущности
- `bid_package`
- `bid_package_item`

### API
- `build_bid_package`

### Зависимости
- M-029

### DoD
- package exists as formal object.

---

## E3. M-031 Bid Completeness Checker
### User stories
- проверить mandatory coverage;
- увидеть blockers before readiness gate.

### Сущности
- `bid_completeness_record`
- `bid_completeness_blocker`
- `bid_completeness_warning`

### API
- `check_bid_completeness`

### Зависимости
- M-014
- M-029
- M-030

### DoD
- blockers explicit;
- completeness status formalized.

---

## E4. M-032 Submission Archive
### User stories
- собрать архив поданной версии заявки;
- сохранить package + receipt evidence в formal archive.

### Сущности
- `submission_archive_record`
- `submission_archive_item`

### API
- `build_submission_archive`

### Зависимости
- M-030
- M-035

### DoD
- archive exists as formal object.

---

## E5. M-033 Tender Procedure Monitor
### User stories
- вести formal monitoring статуса процедуры после подачи;
- видеть timeline, alerts и final outcome context.

### Сущности
- `procedure_monitor_record`
- `procedure_monitor_event`
- `procedure_monitor_alert`

### API
- `build_procedure_monitor`
- `register_procedure_monitor_event`

### Зависимости
- M-032
- M-036
- M-037

### DoD
- monitor timeline explicit;
- alerts explicit.

---

## E6. M-034 Contract Negotiation Workspace
### User stories
- открыть formal workspace контрактования после победы;
- фиксировать issues и comments по договорным условиям.

### Сущности
- `contract_negotiation_record`
- `contract_negotiation_issue`
- `contract_negotiation_comment`

### API
- `build_contract_negotiation_workspace`

### Зависимости
- M-026
- M-033

### DoD
- workspace exists as formal object.
- submission traceable end-to-end.

---

## E6. M-035 Submission Receipt Registry
### User stories
- сохранить proof of submission;
- зафиксировать tracking/portal number.

### Сущности
- `submission_receipt`
- `submission_receipt_artifact`

### API
- `register_submission_receipt`

### Зависимости
- M-033
- M-003

### DoD
- receipt exists as formal record.

---

## E7. M-036 Post-Submission Tracker
### User stories
- вести timeline after submission;
- ловить clarifications and status changes.

### Сущности
- `post_submission_tracker`
- `post_submission_event`

### API
- `record_post_submission_event`
- `update_post_submission_status`

### Зависимости
- M-035

### DoD
- submitted deals stay visible after submission.

---

## E8. M-037 Outcome Intake
### User stories
- formalize award/loss/rejection outcome;
- route to next branch correctly.

### Сущности
- `deal_outcome`

### API
- `register_deal_outcome`

### Зависимости
- M-036

### DoD
- outcome explicit;
- route explicit.

---

# 5. Очередность реализации backlog внутри первой волны

## Sprint 1
- M-001
- M-002
- M-003
- M-004

## Sprint 2
- M-051
- M-055
- M-052

## Sprint 3
- M-008
- M-011
- M-012

## Sprint 4
- M-009
- M-010
- M-013
- M-014
- M-015

## Sprint 5
- M-006
- M-016
- M-017
- M-018

## Sprint 6
- M-019
- M-020
- M-021

## Sprint 7
- M-022
- M-023
- M-024
- M-025

## Sprint 8
- M-026
- M-027
- M-028

## Sprint 9
- M-029
- M-030
- M-031
- M-032

## Sprint 10
- M-033
- M-035
- M-036
- M-037

---

# 6. Главные правила ведения разработки

## Правило 1
Сначала делаем **formal data contracts**, потом UI.

## Правило 2
Каждый модуль должен иметь:
- entity schema;
- event schema;
- API contract;
- DoD.

## Правило 3
Любой human decision — formal record.

## Правило 4
Любой handoff между ветками — explicit status transition + event.

## Правило 5
Любой модуль первой волны должен быть интегрирован с:
- event log;
- orchestrator;
- notifications where needed.

---

# 7. Что делать сразу после этого backlog

После этого документа есть 2 логичных практических шага:

1. сделать **технический backlog Sprint 1** в формате:
   - задача
   - подзадачи
   - сущности
   - endpoints
   - acceptance criteria

2. параллельно собрать **единый data model / entity catalog**, чтобы разработка не расходилась по сущностям.

---

# 8. Итог

Этот backlog — уже не просто архитектура, а **рабочий план сборки первой волны**.

Его задача:
- удерживать структуру;
- не дать потерять ветки;
- помочь тебе и разработчику идти по системе слоями;
- превратить архитектуру в реальную AI-operated тендерную компанию.
