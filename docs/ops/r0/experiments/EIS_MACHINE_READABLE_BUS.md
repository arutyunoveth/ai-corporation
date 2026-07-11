# EIS machine-readable legal-entity bus

## Status

`RECOVERED_NOT_INTEGRATED`

Recovered diagnostics and transport code refer to `services-vbs`, gateway transport modes, and legal-entity infrastructure. The implementation does not establish a verified request/receipt polling state machine, final legal-entity response shape, or an approved customer-flow boundary.

It is therefore not enabled, not deployed, and not interchangeable with `getDocsIP`.

## Boundary

| Contour | Purpose | Status |
|---|---|---|
| `getDocsIP` individual-token path | read-only public procurement documentation | separate production candidate; needs live credential validation |
| `services-vbs` legal-entity machine-readable bus | legal-entity machine-readable exchange | experimental recovery only |

The recovery source and diagnostic artifacts are preserved in recovery commit `4041ac1` and the R0.01 backup. R0 makes no network call or legal-significant submission through either contour.
