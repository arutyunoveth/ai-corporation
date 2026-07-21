# EIS TLS root cause

Confirmed cause: `TRUSTSTORE_NOT_USED` / runtime bootstrap divergence. The failed UI backend was started without the R3 trust-policy environment; the same `.venv-r3` runtime succeeds with the policy, system truststore and direct EIS route.

Verified direct hosts are `zakupki.gov.ru` and `int.zakupki.gov.ru`; both negotiate TLS 1.2 with hostname verification and `CERT_REQUIRED`. `int44-ttls-cert.zakupki.gov.ru` currently returns a TLS handshake failure and is not an approved download/redirect host.

Use `make eis-preflight` before `make r4-local-start`. The bootstrap sources the token environment without printing it, enables the owner-controlled system trust policy, bypasses proxy only for EIS hosts, and refuses insecure fallback.
