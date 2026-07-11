# External blockers

## B-02 — Production ingress and hosting deployment

- Status: `BLOCKED_EXTERNAL`
- Sprint: R0.03/R0.06
- Local work: protected backend boundary and reproducible hosting archive are complete.
- Prerequisite: approved ingress/hosting deployment integration and credentials.
- Next action: deploy the generated archive atomically (live `services/ai-tender-agent.html` is drifted) and point one TLS ingress at `127.0.0.1:8001`.
