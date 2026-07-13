# Known limitations

## PUBLIC_RELIABILITY_LIMITED_NOT_PROVEN

- Status: `KNOWN_LIMITATION`, not a functional R0 blocker.
- CloudPub ingress `https://punctually-ubiquitous-aphid.cloudpub.ru` passed desktop, mobile, LTE/5G, and reboot recovery checks, but no long-term SLA/reliability gate is established.
- This limitation blocks declaring CloudPub permanent production infrastructure and blocks a mass external pilot.

## Operational notes

- After reboot, user `master` must log in and Docker Desktop must start before runtime services are available.
- PostgreSQL is owned by Docker context `desktop-linux` on `127.0.0.1:55432`.
- `completed_with_warnings` remains possible when legacy DOC content is only partially extractable.

These are documented limitations, not unresolved R0 implementation blockers.
