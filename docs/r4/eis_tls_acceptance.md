# EIS TLS acceptance

- Root cause: backend/UI was started without the R3 system-trust bootstrap.
- Exact runtime: `.venv-r3/bin/python` through `make r4-local-start`.
- Trust mode: `system`; custom CA bundle is not required on this macOS runtime.
- Required endpoints: `zakupki.gov.ru`, `int.zakupki.gov.ru` (TLS 1.2, hostname verification, direct route).
- `int44-ttls-cert.zakupki.gov.ru`: optional legacy endpoint; current result is `tls_handshake_failure`; it is not a release blocker and has no insecure fallback.

Cold-start evidence recorded in this session: `make eis-preflight` passed, then `make r4-local-start` started the backend. The UI obtained documentation through getDocsIP for 0116300036226000029, completed deterministic analysis, and exposed the completed report for PDF export. No certificate warning, proxy 502, insecure fallback, or manual certificate action occurred.

Remaining acceptance work: repeat the backend stop/start sequence in a second fresh shell and record the download-host redirect chain before declaring three-cold-start acceptance complete.

## Cold start 2

The first backend was stopped, port 8001 was verified free, and a new `zsh -lc` ran `make eis-preflight` followed by `make r4-local-start`. The backend used `.venv-r3/bin/python`, system trust mode and direct EIS routing. UI getDocsIP for `0116300036226000029` completed, downloaded 9 files, and deterministic analysis completed with terminal status `completed_with_warnings`. PDF export was generated and opened as a one-page PDF.

Archive trace: HTTPS `int.zakupki.gov.ru`, no redirect, HTTP 200, 35,840 bytes, SHA-256 `8ae5789f4835f0fb5f8aa7bb4d610d57763b2197ea29f996a811b2042a06e1c1`; ZIP integrity passed and contains documents. No certificate warning, proxy 502, manual certificate action, wrong runtime, or insecure fallback occurred.
