# R3 operator runbook

## Launch

The owner starts the existing local backend with the protected token environment:

```bash
make eis-preflight
make r4-local-start
```

Open `http://127.0.0.1:8001/demo/tender-agent`.

## Before the session

1. Open the Arvectum URL.
2. Confirm that the page loads and shows the procurement search form.

## For each procurement

1. Enter the procurement number.
2. Start document retrieval.
3. Wait for the final pipeline status.
4. Review the extracted positions.
5. Open the evidence for material conclusions.
6. Review unknown data and risks.
7. Download Web, DOCX, and PDF reports.
8. Record the decision (`go`, `needs_review`, or `no_go`) and a short reason in the pilot log.

Do not edit JSON, access the database, replace documents, or ask a developer to perform an operator step.
