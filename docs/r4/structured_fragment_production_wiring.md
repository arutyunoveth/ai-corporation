# Structured fragment production wiring

## Existing producers

| Source | Existing producer | Current output | Current use |
|---|---|---|---|
| XML purchase objects | `upload_service._extract_supply_items_from_notification_xml` | `SupplyItem` with source row, name, quantity/unit and structured paths | production legacy extraction |
| DOC/DOCX tables | `upload_service._extract_supply_items_from_spec_text` | `SupplyItem` | production legacy extraction |
| XLS/XLSX rows | `upload_service._extract_supply_items_from_xlsx_text` | `SupplyItem` | production legacy extraction |
| Services | `upload_service._extract_service_items_from_nmck_text` | `SupplyItem(item_type=service)` | production legacy extraction |

## Required wiring

```mermaid
flowchart LR
  A[Existing SupplyItem extractors] --> B[StructuredFragmentCollector]
  B --> C[ProcurementSourceGraph]
  C --> D[FieldSourceResolver]
  D --> E[CanonicalProcurementModel]
  E --> F[Report model / Web / PDF / audits]
```

`SupplyItem` must be converted directly to `StructuredSourceFragment` in
memory. Batch CSV is diagnostic output only and must never be read by the
production graph. Goods fragments retain their real source document, row,
extraction strategy and structured paths; service compatibility rows retain
`provenance_kind=adapter` until service structural migration is complete.
