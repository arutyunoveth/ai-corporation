# R0 experiment inventory

| Item | Location recovered | Classification | R0 disposition |
|---|---|---|---|
| Hermes procurement analyser | `src/modules/hermes_agent/` | `EXPERIMENTAL_INTERNAL` | preserved and import-tested; disabled by default (`AI_CORP_HERMES_ENABLED=false`) |
| Tender Research/RAG | `src/tender_research/` | `RECOVERED_AND_CANONICALIZED` | current upstream-compatible implementation is in the R0 baseline; local conflicting alternative remains backed up |
| EIS machine-readable bus/gateway transport | recovery commit `4041ac1`, `eis_soap_transport.py` | `RECOVERED_NOT_INTEGRATED` | retained in recovery/backup only; no production or customer-flow use |
| EIS `getDocsIP` | Tender Operator SOAP client | `READ_ONLY_PRODUCTION_CANDIDATE` | remains separately configured; live credentials/endpoint confirmation is not claimed |
| Runtime data, reports, raw EIS payloads | `data/`, `company_agent_runs/`, `tmp/` | `LOCAL_RUNTIME_DATA` | archived outside Git; not committed |

No recovered experiment is represented as a client-validated production feature.
