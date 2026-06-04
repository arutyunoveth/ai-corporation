# Entity Catalog Recovery Sprint R1

## M-005 Customer Registry

### Canonical refs

- `customer_id` => `CUS-YYYY-NNNNNN`

### Tables

- `customer_profiles`
- `customer_external_refs`
- `customer_contours`

### Enums

- `CustomerStatus`: `ACTIVE`, `INACTIVE`, `PROSPECT`

## M-007 Tender Import

### Canonical refs

- `tender_import_run_id` => `TIR-YYYY-NNNNNN`
- `tender_import_event_id` => `TIE-YYYY-NNNNNN`

### Tables

- `tender_import_runs`
- `tender_import_events`
- `tender_import_payloads`

### Enums

- `TenderImportRunStatus`: `STARTED`, `SUCCEEDED`, `FAILED`

## M-008 Tender Normalization

### Canonical refs

- `tender_normalization_set_id` => `TNS-YYYY-NNNNNN`
- `tender_normalization_id` => `TN-YYYY-NNNNNN`

### Tables

- `tender_normalization_sets`
- `tender_normalization_records`
- `tender_normalization_links`

### Enums

- `TenderNormalizationStatus`: `BUILT`, `FAILED`, `STALE`

## M-010 Intake Priority

### Canonical refs

- `intake_priority_set_id` => `IPS-YYYY-NNNNNN`
- `intake_priority_id` => `IP-YYYY-NNNNNN`

### Tables

- `intake_priority_sets`
- `intake_priority_records`
- `intake_priority_factors`

### Enums

- `PrioritizationStatus`: `BUILT`, `FAILED`, `STALE`

## M-012 Requirement Extraction

### Canonical refs

- `requirement_extraction_set_id` => `RES-YYYY-NNNNNN`
- `requirement_extraction_id` => `REQ-YYYY-NNNNNN`

### Tables

- `requirement_extraction_sets`
- `requirement_extraction_records`
- `requirement_source_links`

### Enums

- `RequirementExtractionStatus`: `BUILT`, `FAILED`, `STALE`

## DTO Contracts

- `CreateCustomerRequest`
- `CreateTenderImportRunRequest`
- `BuildTenderNormalizationRequest`
- `BuildIntakePriorityRequest`
- `BuildRequirementExtractionRequest`
