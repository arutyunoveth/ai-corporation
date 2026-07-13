# R0 final report

## Executive result

`R0_CLOSED_FUNCTIONALLY`. Product functional SHA `2578d114074685ddb072736839b6023897105bcd` and site production SHA `9b87212500b48ec918973f0e38351a5ad14b2603` are frozen. Live procurement search, getDocsIP, processing, analysis, DOCX/PDF, cross-browser, LTE/5G, cookie consent, and post-reboot acceptance passed.

## Sprint result

| Sprint | Status |
|---|---|
| R0.01 backup | DONE |
| R0.02 reconciliation | DONE |
| R0.03 runtime artifacts | DONE |
| R0.04 security | DONE |
| R0.05 CI | DONE |
| R0.06 site package | DONE |
| R0.07 docs | DONE |
| R0.08 validation/release | superseded by R0.09 |
| R0.09 operational closure | DONE; product/site CI green; site merged |
| R0.10 Git/site/docs closure | DONE |

## Checks

- Backup: Git bundle, data archive, and two PostgreSQL dumps verified.
- Product focused reconciliation: 156 passed.
- Security/middleware: 6 passed.
- Site: GitHub CI green; `npm ci`, `npm run check`, canonical main archive build, generated production build-info, and `unzip -t` passed.
- Live site smoke: apex, health/API health, robots, sitemap, cookie consent and agent flow passed. Any pre-deploy drift is classified `DETECTED_EXPECTED_PRE_DEPLOY` and does not block functional closure.
- Runtime preflight: PASS after isolated Docker pgvector `55432`, launchd backend/embeddings, and Ollama `11434` normalization.

## Backups

- PostgreSQL dump: `/Users/master/arvectum-backups/postgres/20260713T141620Z/arvectum-postgres.dump` (1,092,244 bytes; SHA256 `4300f65a26afa3babbbfd40a1ba1dfe55b0b5a932f78c7a96e44c056d90df5d7`).
- Site backup: `/Users/master/arvectum-backups/reg-ru/cookie-hotfix-20260713T144750Z/document-root.tgz`.
- Previous site backup: `/Users/master/arvectum-backups/reg-ru/20260712T113741Z/document-root.tgz`; remote `/var/www/u3542630/data/backups/arvectum-site/20260712T113741Z/document-root.tgz` (SHA256 `6c507a1b6a90292e4bdd58af5eeceeb5fe7c8f8daf2b37c13f2ba81e95ac6c3a`).

## Known limitation

CloudPub remains temporary ingress. Long-term public reliability/SLA is not proven: `PUBLIC_RELIABILITY_LIMITED_NOT_PROVEN`. This is not a functional R0 blocker, but it blocks declaring CloudPub permanent production infrastructure or starting a mass external pilot.

No new platform modules or pilot were started.
