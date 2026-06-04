# MVP-ядро первой волны разработки — roadmap и ТЗ верхнего уровня

## 1. Назначение документа

Этот документ фиксирует **первую волну реальной разработки**.  
Его цель — перевести полную архитектуру в **практический порядок реализации**, чтобы:

- не пытаться строить все сразу;
- не потерять системность;
- не уйти в бесконечное проектирование;
- дать Codex/разработчику понятный implementation roadmap.

---

## 2. Главная цель первой волны

Первая волна должна дать тебе **рабочую ИИ-компанию для цикла:**

> вход закупки → анализ → supplier-side → экономика/риск → твое решение → сбор заявки → подача → фиксация исхода

Это уже достаточное ядро, чтобы:
- реально участвовать в закупках;
- получать кейсы;
- обкатывать AI workforce;
- готовить будущий SaaS-контур.

---

## 3. Что считается результатом первой волны

Первая волна считается успешной, если система умеет:

1. принять закупку и завести deal;
2. проанализировать документы и требования;
3. подобрать поставщиков и собрать ТКП;
4. посчитать экономику, кассовый разрыв и риски;
5. вывести сделку на твое go/no-go решение;
6. собрать и проверить заявку;
7. провести controlled submission;
8. зафиксировать outcome сделки;
9. сохранить полный audit trail.

---

## 4. Архитектурный принцип первой волны

Первая волна строится в 5 implementation blocks:

### Block A. Platform skeleton
Фундамент, без которого нельзя запускать процесс.

### Block B. Intake & analysis
Вход закупки и извлечение структуры требований.

### Block C. Supplier engine
Вся работа с поставщиками и ТКП.

### Block D. Finance / risk / approval
Принятие решения по сделке.

### Block E. Bid / submission / outcome
Подготовка заявки, подача, receipt и outcome.

---

## 5. Первая волна по этапам

## Этап 1. Platform skeleton

### Модули
- M-001 Deal Registry
- M-002 Status Model Engine
- M-003 Document Store
- M-004 Event Log & Decision Journal
- M-051 Workflow Orchestrator
- M-055 Integration Bus / Connectors Layer
- M-052 Notification Layer

### Что делаем
- создаем canonical deal entity;
- создаем status graph;
- создаем единое document storage;
- создаем event/audit model;
- создаем базовый orchestration runtime;
- создаем единый слой интеграций;
- создаем базовый notification path.

### Результат этапа
Появляется исполняемый каркас системы.

### Definition of Ready для перехода дальше
- можно создать сделку;
- можно менять ее статус только по allowed transitions;
- можно писать события в лог;
- можно запускать workflow runs;
- есть минимум один рабочий канал уведомлений;
- есть минимум один рабочий connector path.

---

## Этап 2. Intake & analysis

### Модули
- M-008 Tender Intake Pipeline
- M-009 Tender Screening Engine
- M-010 Priority Scoring Engine
- M-011 Document Ingestion Layer
- M-012 Tender Summary Builder
- M-013 Compliance Matrix Builder
- M-014 Document Requirement Extractor
- M-015 Initial Tech Risk Flags

### Что делаем
- intake закупки из внешнего источника;
- ingest документов;
- screening на go/no-go candidate level;
- priority score;
- summary закупки;
- compliance matrix;
- checklist документов;
- ранние техриски.

### Результат этапа
Сделка превращается из “тендера в сыром виде” в структурированный объект анализа.

### Definition of Ready для перехода дальше
- по сделке уже есть summary;
- есть matrix требований;
- есть список required docs;
- есть early risk flags;
- candidate уже либо отсеян, либо проходит дальше.

---

## Этап 3. Supplier engine

### Модули
- M-006 Supplier Registry
- M-016 Supplier Search
- M-017 RFQ Generator
- M-018 Supplier Communication Tracker
- M-019 TKP Repository
- M-020 Supplier Verification
- M-021 Quote Comparison Engine

### Что делаем
- создаем supplier registry;
- ищем shortlist;
- генерируем RFQ;
- трекаем коммуникацию;
- регистрируем ТКП;
- верифицируем поставщиков;
- сравниваем предложения.

### Результат этапа
Появляется supplier-side engine, который превращает “нужно найти поставщика” в formal comparison-ready supplier offers.

### Definition of Ready для перехода дальше
- минимум один supplier shortlist получен;
- отправка RFQ formalized;
- входящие ТКП formalized;
- supplier comparison построен;
- есть базовая supplier verification.

---

## Этап 4. Finance / risk / approval

### Модули
- M-022 Cost Model Engine
- M-023 Cash Gap Calculator
- M-024 Financing Strategy Engine
- M-025 Finance Memo Builder
- M-026 Contract Risk Parser
- M-027 Integrated Risk Memo Builder
- M-028 CEO Approval Cockpit

### Что делаем
- считаем internal cost model;
- считаем cash gap;
- строим financing scenarios;
- собираем finance memo;
- разбираем проект договора;
- собираем integrated risk memo;
- выводим сделку на твое решение.

### Результат этапа
Сделка получает formal decision layer: экономика, риск и управленческий approval.

### Definition of Ready для перехода дальше
- по сделке есть finance memo;
- есть integrated risk memo;
- есть contract risk parse;
- есть твое formal decision record.

---

## Этап 5. Bid / submission / outcome

### Модули
- M-029 Bid Document Collector
- M-030 Bid Package Builder
- M-031 Bid Completeness Checker
- M-032 Submission Archive
- M-033 Tender Procedure Monitor
- M-034 Contract Negotiation Workspace
- M-035 Supplier Back-to-Back Contract Draft
- M-036 Execution Plan Builder
- M-037 Purchase Order Manager
- M-038 Supplier Progress Monitor

### Что делаем
- собираем source docs заявки;
- строим package;
- проверяем completeness;
- проводим readiness gate;
- проводим controlled submission;
- регистрируем proof of submission;
- трекаем post-submission events;
- формализуем outcome.

### Результат этапа
Цикл первой волны замыкается: система умеет не только анализировать, но и реально доводить сделку до подачи и результата.

### Definition of Done первой волны
- хотя бы одна реальная закупка проходит end-to-end через систему;
- pipeline не разваливается между этапами;
- owner decision formalized;
- submission formalized;
- outcome formalized;
- audit trail целостный.

---

## 6. Что делаем после первой волны

После того как первая волна стабильно работает, переходим во вторую:

### Wave 2A. Execution branch
- M-039
- M-040
- M-041
- M-042
- M-043
- M-044
- M-045
- M-046

### Wave 2B. System governance and platform excellence
- M-038
- M-047
- M-048
- M-049
- M-050
- M-053
- M-054

---

## 7. Порядок реальной сборки внутри разработки

Ниже более практический порядок для Codex / разработчика.

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

## 8. Главные правила реализации

### Правило 1
Сначала строим **formal records and schemas**, потом UI.

### Правило 2
Каждый модуль должен сначала получить:
- entity model;
- event model;
- status model;
- integration points.

### Правило 3
Нельзя автоматизировать модуль, пока не определен:
- его вход;
- его выход;
- его owner/agent;
- его Definition of Done.

### Правило 4
Сначала делаем **happy path**, потом edge cases.

### Правило 5
Никаких hidden rules в коде — все thresholds и policies должны уехать в governance layer.

---

## 9. ТЗ верхнего уровня для разработчика

Разработчик должен воспринимать первую волну как создание **process operating system для тендерной компании**.

### Обязательные технические принципы
- event-driven architecture;
- canonical entity storage;
- versioned documents and artifacts;
- explicit status machine;
- audit-first design;
- schema-first inter-module contracts;
- module isolation with clear APIs;
- no hidden logic in UI;
- no hardcoded prompt blobs in domain services;
- observability hooks from day one.

### Обязательные бизнесовые принципы
- один человек должен видеть и понимать весь pipeline;
- никакая критичная точка не должна быть “серой зоной”;
- любое решение должно быть traceable;
- любая автоматизация должна иметь human escalation path;
- submission и approval — только formal objects.

---

## 10. Главный итог

Если первую волну сделать правильно, ты получишь не набор скриптов, а уже **рабочую операционную систему тендерной компании**, где:
- ты один;
- ИИ закрывает функции тендерного отдела;
- pipeline прозрачен;
- решения traceable;
- можно реально показывать кейсы будущим клиентам SaaS-направления.

Этот документ надо использовать как **основное ТЗ верхнего уровня на первую реализацию**.
