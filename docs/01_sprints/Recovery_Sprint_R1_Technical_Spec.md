# Recovery Sprint R1 Technical Spec

## Назначение

Recovery Sprint R1 восстанавливает канонические модули `M-005`, `M-007`, `M-008`, `M-010`, `M-012` внутри locked master-registry `M-001..M-055` без destructive refactor.

## Scope

- `M-005` Customer Registry
- `M-007` Tender Import
- `M-008` Tender Normalization
- `M-010` Intake Summary / Prioritization
- `M-012` Requirement Extraction

## Ограничения

1. Не вводить новые canonical IDs.
2. Не переписывать старые миграции.
3. Не ломать существующие endpoints и тесты.
4. Reuse drift-логики допускается только как internal helper contour.

## Acceptance

### M-005

- customer profile создается и читается через `POST/GET/PATCH /customers`
- external refs и procurement contours persisted
- query по `inn` и имени работает
- event trace exists

### M-007

- `tender_import_runs`, `tender_import_events`, `tender_import_payloads` persisted
- raw payload не смешивается с normalization layer
- source metadata preserved
- event trace exists

### M-008

- normalization set строится от `tender_import_event_id`
- normalized procurement number, title, customer, deadline persisted
- deal/customer links persisted
- output пригоден для downstream screening/prioritization
- event trace exists

### M-010

- intake summary persisted как formal artifact
- priority score и factors persisted отдельно
- output queryable by `deal_id`
- event trace exists

### M-012

- requirement extraction живет как отдельный canonical module
- extraction records и source links persisted
- current legacy tender summary helper не ломается
- event trace exists
