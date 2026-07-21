# Closed-pilot staging stack

This is an isolated, localhost-only deployment package for the R6 release. Set `PILOT_SECRET_ENV` to an external `0600` env file and `PILOT_TLS_POLICY` to the external trust policy, run `scripts/preflight.sh`, then `docker compose -f compose.yaml up -d --build`. It does not deploy publicly or expose PostgreSQL/API ports.
