# Arvectum R0 status

## Product snapshot

Stage: `R0_CLOSED_FUNCTIONALLY`. Product functional SHA is `2578d114074685ddb072736839b6023897105bcd`; site production SHA is `9b87212500b48ec918973f0e38351a5ad14b2603`. The MVP supports controlled tender intake, read-only `getDocsIP`, extraction, RAG-assisted analysis, local-model integration, and human-reviewed DOCX/PDF export.

## Runtime

Canonical runtime checkout: `/Users/master/arvectum-runtime/AI-Corporation` on `main`. Runtime user is `master`; backend is `127.0.0.1:8001`, PostgreSQL is `127.0.0.1:55432` in Docker context `desktop-linux` (`arvectum-postgres`, `unless-stopped`), embeddings are `127.0.0.1:8090` (`com.arvectum.embeddings`), and Ollama is `127.0.0.1:11434`.

Actual baseline: Docker pgvector PostgreSQL is healthy on host port `55432`; the unrelated `5432` PostgreSQL remains untouched. Backend and embeddings are launchd-managed and healthy. Temporary ingress is `https://punctually-ubiquitous-aphid.cloudpub.ru`; public site is `https://arvectum.com`.

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

Functional acceptance, LTE/5G, cookie consent, and post-reboot autostart are PASS. CloudPub is temporary and its long-term public reliability/SLA is not proven (`PUBLIC_RELIABILITY_LIMITED_NOT_PROVEN`). After reboot, login of `master` and Docker Desktop startup are required. `completed_with_warnings` remains possible for legacy DOC extraction.

## Next milestone

R0 is functionally closed. Next stage is limited to extraction quality, analysis quality, report structure, and evidence coverage; no mass external pilot is authorized by this baseline.
