# Tender Agent Demo — Acceptance Checklist

Pass/fail checklist for customer demo readiness of the Tender Operator Agent Demo console.

## 1. Console loads

- [ ] `GET /demo/tender-agent` returns 200 in < 3 s
- [ ] Header shows "Тендерный агент" with badge row (Демо-режим / подтверждение человеком, Пилотный контур, Без внешних действий)
- [ ] 5 tabs render: Найти закупку, Получить документацию по номеру, Загрузить документы, Демо-набор, Профиль поставщика
- [ ] No browser console errors (4xx/5xx, uncaught JS)

## 2. Supplier profile tab

- [ ] Profile tab shows supplier name, INN, categories, regions, price range, keywords, stop-words, risk preferences, certificates
- [ ] "Сбросить профиль на демо-настройки" button works → flash confirmation
- [ ] No secrets (tokens, passwords, full archive URLs) leaked in profile display

## 3. Search tab — demo_local source

- [ ] Default query "электротехническое оборудование" pre-filled
- [ ] Click "Найти закупки" returns 10+ demo results
- [ ] Each card shows: title, number, customer, law, price, dates, attachments status
- [ ] "Создать run и загрузить документы вручную" button present for demo records
- [ ] No English labels visible in card or form

## 4. Search tab — public 44‑ФЗ search

- [ ] Select "Публичный поиск ЕИС 44-ФЗ", query "электротехническое оборудование"
- [ ] Cards render with relevance score badge (цветной chip с %) and breakdown panel
- [ ] Badge threshold: ≥65 % = высокая, ≥40 % = средняя, ≥20 % = низкая, <20 % = не рекомендовано
- [ ] "Получить документацию и анализировать" button present on cards with reestr_number
- [ ] "Открыть в ЕИС" link present
- [ ] Relevance reasons are in Russian, technical (refId, archiveUrl, SOAP method) labels are hidden from customer-facing card

## 5. EIS docs tab — getDocsIP flow

- [ ] "Диагностика getDocsIP" panel loads automatically
- [ ] Form pre-filled with reestrNumber `0888200000224000038`
- [ ] Submit creates a run, shows result with: run ID, SOAP status, archive status, extracted file count, links to run/report
- [ ] Full archive URL and ticket NOT displayed in UI (only host/path summary)
- [ ] Run appears in "Последние прогоны" on upload tab
- [ ] If archiveUrl not present → manual upload fallback triggered

## 6. Upload tab — run detail

- [ ] Selected run shows: title, run ID, status, category, customer, file list, warnings
- [ ] EIS source block renders (if applicable): реестровый номер, SOAP-метод, ID запроса, archiveUrl, archive download status, file count
- [ ] "Открыть HTML-отчёт" link works → report opens
- [ ] Report shows all blocks: source, profile, EIS docs, requirements, questions, RFQ, quotes, economics, risks, recommendation, trace
- [ ] Report labels are in Russian, no English technical IDs

## 7. Report pages

- [ ] `GET /demo/tender-agent/report` returns 200 — synthetic demo report
- [ ] Badges in Russian (Демо-режим / подтверждение человеком, Синтетические данные / без внешних действий)
- [ ] Uploaded run report HTML at `/demo/tender-agent/runs/<id>/report` — section cards render correctly
- [ ] Procurement blocked report shows warning + manual upload instructions (English badges now in Russian)

## 8. No secrets leak

- [ ] No ZAKUPKI_GOV_RU_SOAP_TOKEN value displayed anywhere
- [ ] No full archive URL or ticket query parameter shown
- [ ] No .env.local path or content
- [ ] Diagnostics panel shows only host/path, not full URL with credentials
- [ ] HTML source does not contain token/secret values

## 9. UI language consistency

- [ ] All button labels, section titles, badges, and empty-state messages in Russian
- [ ] No English technical IDs (configured=true, token_present, last_status) in customer-visible text
- [ ] Formatting: money in "1 234,56 ₽" (ru-RU locale), dates in Russian format, booleans как "да"/"нет"

## 10. Safety constraints

- [ ] No "подать заявку", "отправить поставщику", "ЭЦП", "captcha bypass" buttons
- [ ] Human-in-the-loop calls to action explicitly marked: "Что проверить человеку", "Ручные проверки"
- [ ] Pipeline description shows "Без внешних действий" badge
