# R0 pilot security baseline

The backend has a single-instance pilot boundary, not IAM or multi-tenancy.

- Public: `/health` only.
- Protected when `AI_CORP_PILOT_AUTH_ENABLED=true`: `/api`, `/demo`, `/pilot`, docs/OpenAPI, and `/health/ready`.
- Authentication: environment-configured Basic Auth with timing-safe comparison; empty and known placeholder passwords are rejected at startup.
- Protected responses: `no-store`, `nosniff`, deny framing, and no-referrer headers.
- Host/CORS: configured from `AI_CORP_ALLOWED_HOSTS` and `AI_CORP_CORS_ALLOW_ORIGINS`; production examples contain no wildcard.
- Hermes remains disabled by default; the EIS legal-entity bus is not exposed.

Non-goals: SSO, user management, tenant isolation, fine-grained RBAC, automatic submission, or EDS integration.
