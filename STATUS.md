# Arvectum R0 status

## Product snapshot

Stage: closed design-partner pilot baseline. The MVP supports controlled tender intake, read-only `getDocsIP` documentation retrieval where configured, manual upload/extraction, RAG-assisted analysis, local-model integration, and export with human review. It does not submit bids, sign documents, provide SaaS/multi-tenancy, mobile, OCR, 223-FZ, or new autonomous agents.

## Runtime

Canonical integration checkout: `/Users/master/Documents/AI-Corporation-r0` on `codex/r0-sync-2026-07-11`. Target ports are backend `8001`, PostgreSQL `55432`, LLM `8088`, embeddings `8090`.

Actual preflight: local PostgreSQL remains on `5432`; LLM `8088` is listening; embeddings `8090` is unavailable; backend `8001` is not running. The runtime is therefore **not deployed**. Backup: `/Users/master/Documents/arvectum-r0-backups/20260711-145008`.

## Capability matrix

| Block | In Git | Local verification | Deployed | Client verified |
|---|---|---|---|---|
| public 44-FZ search / getDocsIP / manual upload / extraction | yes | focused tests | no | no |
| RAG / local LLM / export / jobs | yes | focused tests | no | no |
| pilot auth | yes | security tests | no | no |
| Hermes | experimental internal | focused tests | no | no |
| EIS machine-readable bus | recovery only | no stable flow | no | no |
| OCR / RFQ-TKP / submission-EDS / SaaS / mobile | out of R0 | n/a | no | no |

## Known limitations

Runtime port cutover and embeddings service are pending. Hosting deployment and ingress credentials were not available. `getDocsIP` is separate from the experimental legal-entity bus and needs live credential validation.

## Next milestone

Design-partner pilot on 3–5 real procurements.
