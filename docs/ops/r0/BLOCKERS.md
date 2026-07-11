# External blockers

## B-01 — Runtime dependency cutover

- Status: `BLOCKED_DATA`
- Sprint: R0.03/R0.08
- Local work: port-55432 compose config, runtime scripts, preflight and launchd template are complete.
- Prerequisite: migrate or configure the existing Homebrew PostgreSQL runtime to the target contour and provide/start an embeddings service at `127.0.0.1:8090`.
- Next action: apply the runbook in a maintenance window, then run preflight and smoke.

## B-02 — Production ingress and hosting deployment

- Status: `BLOCKED_EXTERNAL`
- Sprint: R0.03/R0.06
- Local work: protected backend boundary and reproducible hosting archive are complete.
- Prerequisite: approved ingress/hosting deployment integration and credentials.
- Next action: deploy the generated archive atomically (live `services/ai-tender-agent.html` is drifted) and point one TLS ingress at `127.0.0.1:8001`.

## B-03 — GitHub governance publication

- Status: `BLOCKED_EXTERNAL`
- Sprint: R0.05/R0.08
- Local work: CI workflows and branch-protection script are committed.
- Prerequisite: final review of the R0 branch before branch protection/PR publication.
- Next action: push branch, open draft PR, then apply `scripts/github/apply_branch_protection.sh` if desired.
