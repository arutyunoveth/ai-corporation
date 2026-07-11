# External blockers

## B-02 — Production hosting credentials and publication

- Status: `BLOCKED_EXTERNAL`
- Sprint: R0.03/R0.06
- Local work: protected backend boundary and reproducible hosting archive are complete.
- Prerequisite: approved ingress/hosting deployment integration and credentials.
- Classification: `DETECTED_EXPECTED_PRE_DEPLOY`; live drift does not block merge.
- Next action: deploy the generated archive atomically after credentials are available.

## B-03 — Production TLS ingress

- Status: `BLOCKED_EXTERNAL`
- No Tailscale Funnel or public backend exposure was configured in R0.10.
- Next action: configure one approved TLS ingress during the separate publication step.

## B-04 — GitHub branch protection permissions

- Status: `BLOCKED_EXTERNAL_BRANCH_PROTECTION_PERMISSION`
- Safe protection updates were attempted; GitHub permissions/plan do not allow the required ruleset update.
- Required capability: repository administration permission and a plan supporting protected private branches/rulesets.
- Product required checks: `quality`, `migrations`, `security`; site required check: `CI`.
