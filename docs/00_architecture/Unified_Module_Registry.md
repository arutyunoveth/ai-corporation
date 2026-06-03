# Единый реестр модулей ИИ-компании для тендерного бизнеса

## 1. Назначение документа

Этот документ — **единый реестр модулей системы**.  
Его задача — держать в одном месте:
- полный список модулей;
- их роль в компании;
- принадлежность к контуру;
- приоритет;
- примерную очередность реализации;
- зависимость от бизнес-этапов.

Этот реестр нужен как **главная навигационная карта** для разработки, автоматизации и дальнейшей декомпозиции.

---

## 2. Логика группировки

Модули сгруппированы по 8 большим контурам:

1. **Core / Базовый каркас сделки**
2. **Tender intake и ранний анализ**
3. **Supplier-side контур**
4. **Finance / Risk / Approval контур**
5. **Bid preparation / Submission контур**
6. **Post-submission / Outcome / Execution контур**
7. **System governance / AI runtime контур**
8. **Platform / Observability / Dashboard / Integrations**

---

## 3. Реестр модулей

## 3.1 Core / Базовый каркас сделки

| ID | Название | Контур | Приоритет | Роль |
|---|---|---|---|---|
| M-001 | Deal Registry | Core | P0 | Канонический реестр сделок |
| M-002 | Status Model Engine | Core | P0 | Статусная модель и allowed transitions |
| M-003 | Document Store | Core | P0 | Единое хранилище документов и артефактов |
| M-004 | Event Log & Decision Journal | Core | P0 | Журнал событий, решений и аудита |
| M-005 | Counterparty / Customer Registry | Core | P1 | Реестр заказчиков и контрагентного контекста |
| M-006 | Supplier Registry | Core | P0 | Реестр поставщиков |
| M-007 | Deal Workspace Projection | Core | P1 | Проекция состояния сделки для рабочих экранов |

---

## 3.2 Tender intake и ранний анализ

| ID | Название | Контур | Приоритет | Роль |
|---|---|---|---|---|
| M-008 | Tender Intake Pipeline | Intake | P0 | Первичный intake закупки |
| M-009 | Tender Screening Engine | Intake | P0 | Быстрый отсев неподходящих закупок |
| M-010 | Priority Scoring Engine | Intake | P0 | Приоритизация кандидатов |
| M-011 | Document Ingestion Layer | Intake | P0 | Нормализованный ingest файлов и вложений |
| M-012 | Tender Summary Builder | Intake | P0 | Сводка закупки для человека и модулей |
| M-013 | Compliance Matrix Builder | Intake | P0 | Матрица требований |
| M-014 | Document Requirement Extractor | Intake | P0 | Извлечение checklist документов |
| M-015 | Initial Tech Risk Flags | Intake | P0 | Ранние техриски и ambiguity flags |

---

## 3.3 Supplier-side контур

| ID | Название | Контур | Приоритет | Роль |
|---|---|---|---|---|
| M-016 | Supplier Search | Supplier | P0 | Поиск и shortlist поставщиков |
| M-017 | RFQ Generator | Supplier | P0 | Генерация запросов на ТКП |
| M-018 | Supplier Communication Tracker | Supplier | P0 | Трекинг коммуникации с поставщиками |
| M-019 | TKP Repository | Supplier | P0 | Репозиторий входящих ТКП |
| M-020 | Supplier Verification | Supplier | P0 | Базовая верификация поставщиков |
| M-021 | Quote Comparison Engine | Supplier | P0 | Сравнение предложений поставщиков |

---

## 3.4 Finance / Risk / Approval контур

| ID | Название | Контур | Приоритет | Роль |
|---|---|---|---|---|
| M-022 | Cost Model Engine | Finance | P0 | Внутренняя себестоимость сделки |
| M-023 | Cash Gap Calculator | Finance | P0 | Расчет кассового разрыва |
| M-024 | Financing Strategy Engine | Finance | P0 | Сценарии финансирования |
| M-025 | Finance Memo Builder | Finance | P0 | Финансовое memo |
| M-026 | Contract Risk Parser | Risk | P0 | Разбор рисков проекта договора |
| M-027 | Integrated Risk Memo Builder | Risk | P0 | Единый risk memo |
| M-028 | CEO Approval Cockpit | Approval | P0 | Формальная точка человеческого решения |

---

## 3.5 Bid preparation / Submission контур

| ID | Название | Контур | Приоритет | Роль |
|---|---|---|---|---|
| M-029 | Bid Document Collector | Bid Prep | P0 | Сбор документов заявки |
| M-030 | Bid Package Builder | Bid Prep | P0 | Формальная сборка пакета заявки |
| M-031 | Bid Completeness Checker | Bid Prep | P0 | Проверка комплектности |
| M-032 | Submission Readiness Gate | Bid Prep | P0 | Финальный readiness gate |
| M-033 | Submission Control | Submission | P0 | Контролируемая подача заявки |
| M-035 | Submission Receipt Registry | Submission | P0 | Доказательства подачи |
| M-036 | Post-Submission Tracker | Submission | P0 | Трекинг статуса после подачи |
| M-037 | Contract Award / Loss Decision Intake | Submission | P0 | Formal intake результата закупки |

---

## 3.6 Outcome / Execution / Closure контур

| ID | Название | Контур | Приоритет | Роль |
|---|---|---|---|---|
| M-038 | Win/Loss Postmortem | Learning | P1 | Разбор исхода сделки |
| M-039 | Delivery Launch Control | Execution | P0 | Запуск исполнения по выигранной сделке |
| M-040 | Execution Command Center | Execution | P0 | Центральный cockpit исполнения |
| M-041 | Delivery Milestone Tracker | Execution | P0 | Контроль milestones |
| M-042 | Supplier Fulfillment Tracker | Execution | P0 | Vendor-side исполнение |
| M-043 | Shipping & Acceptance Tracker | Execution | P0 | Отгрузка, доставка, приемка |
| M-044 | Payment Collection Tracker | Execution | P0 | Дебиторка и сбор оплаты |
| M-045 | Incident & Escalation Desk | Execution | P0 | Инциденты и эскалации |
| M-046 | Deal Closure & Archive | Closure | P0 | Закрытие и архив сделки |

---

## 3.7 System governance / AI runtime контур

| ID | Название | Контур | Приоритет | Роль |
|---|---|---|---|---|
| M-047 | KPI & Learning Loop | Governance | P0 | KPI и learning loop |
| M-048 | Admin & Policy Console | Governance | P0 | Управление policies и thresholds |
| M-049 | Agent Registry | AI Runtime | P0 | Реестр ИИ-сотрудников |
| M-050 | Prompt / Schema Library | AI Runtime | P0 | Библиотека prompt/schema assets |
| M-051 | Workflow Orchestrator | AI Runtime | P0 | Оркестратор всей компании |
| M-052 | Notification Layer | AI Runtime | P0 | Слой сигналов и уведомлений |

---

## 3.8 Platform / Observability / Dashboard / Integrations

| ID | Название | Контур | Приоритет | Роль |
|---|---|---|---|---|
| M-053 | Observability & Audit Console | Platform | P0 | Диагностика, аудит, наблюдаемость |
| M-054 | Master Dashboard | Platform | P0 | Главная owner-панель |
| M-055 | Integration Bus / Connectors Layer | Platform | P0 | Единый слой интеграций |

---

## 4. Что является MVP-ядром

Не все модули нужны в первой волне.  
Для первого рабочего контура компании нужен **операционный MVP-коридор**:

### 4.1 Обязательное MVP-ядро
- M-001
- M-002
- M-003
- M-004
- M-006
- M-008
- M-009
- M-010
- M-011
- M-012
- M-013
- M-014
- M-015
- M-016
- M-017
- M-018
- M-019
- M-020
- M-021
- M-022
- M-023
- M-024
- M-025
- M-026
- M-027
- M-028
- M-029
- M-030
- M-031
- M-032
- M-033
- M-035
- M-036
- M-037
- M-051
- M-052
- M-055

### 4.2 Вторая волна
- M-005
- M-007
- M-038
- M-039
- M-040
- M-041
- M-042
- M-043
- M-044
- M-045
- M-046
- M-047
- M-048
- M-049
- M-050
- M-053
- M-054

---

## 5. Итог

Если смотреть на систему сверху, то:
- **M-001–M-007** — это позвоночник данных и статусов;
- **M-008–M-015** — intake и ранний анализ;
- **M-016–M-021** — supplier-side engine;
- **M-022–M-028** — экономика, риски и финальное решение;
- **M-029–M-037** — заявка, подача и capture outcome;
- **M-039–M-046** — исполнение и закрытие;
- **M-047–M-055** — управление всей ИИ-компанией как системой.

Этот документ надо использовать как:
1. **главный реестр архитектуры**;
2. **базу для roadmap**;
3. **оглавление для Codex / разработчика**;
4. **контрольный список, чтобы ни одна ветка не потерялась**.
