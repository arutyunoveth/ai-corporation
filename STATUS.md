# Arvectum R0 status

## Product snapshot

Stage: `R0_CODE_AND_RUNTIME_COMPLETE_PRODUCTION_PUBLICATION_PENDING`. The MVP supports controlled tender intake, read-only `getDocsIP` documentation retrieval where configured, manual upload/extraction, RAG-assisted analysis, local-model integration, and export with human review. It does not submit bids, sign documents, provide SaaS/multi-tenancy, mobile, OCR, 223-FZ, or new autonomous agents.

## Runtime

Canonical runtime checkout: `/Users/master/arvectum-runtime/AI-Corporation` on `main`. Runtime ports are backend `8001`, PostgreSQL `55432`, Ollama OpenAI-compatible LLM `11434`, and embeddings `8090`.

Actual baseline: Docker pgvector PostgreSQL is healthy on host port `55432`; the unrelated `5432` PostgreSQL remains untouched. Backend and embeddings are launchd-managed and healthy on `8001` and `8090`; Ollama on `11434` is the canonical LLM owner. Port `8088` is an unrelated HTTP service and is not used. Backup: `/Users/master/Documents/arvectum-r0-backups/20260711-145008`.

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

Runtime cutover, embeddings, backend auth, and launchd ownership are complete and verified. Hosting deployment and TLS ingress credentials were not available. `getDocsIP` is separate from the experimental legal-entity bus and needs live credential validation.

## Next milestone

Production publication and TLS ingress remain external steps; no pilot was started in R0.10.
