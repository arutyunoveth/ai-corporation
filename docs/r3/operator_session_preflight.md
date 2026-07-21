# R3 operator session preflight

Status: `R3_OPERATOR_SESSION_READY`

Baseline: `172a041f36bf652dd2436323518bcec3122be9d8`

Branch: `codex/r3-operator-pilot`

## Checks

| Check | Result | Evidence |
|---|---|---|
| Clean R3 worktree | PASS | Worktree is clean before preparation artifacts |
| Baseline | PASS | HEAD is the requested baseline SHA |
| Real EIS discovery | BLOCKED | Current proxy returns `HTTP/1.0 502 Bad Gateway` for CONNECT to `zakupki.gov.ru:443` |
| Direct/NO_PROXY route | BLOCKED | DNS and TCP succeed to `95.167.245.92:443`, but local TLS verification fails with `unable to get local issuer certificate` |
| getDocsIP smoke | BLOCKED | Known number `0352300080626000109` returns `EisMissingTokenError` in current, direct, and explicit-NO_PROXY environments |
| Candidate pool of at least 30 | BLOCKED | Public search direct path returned 10 search candidates, but no candidate can pass required getDocsIP verification without the configured EIS SOAP token |
| Project environment | PASS | `.venv-r3` uses Python 3.11.15; declared dev dependencies installed |
| HTTPS with certifi | BLOCKED | `httpx` with `verify=certifi.where()` and `trust_env=False` still reports `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` |
| HTTPS with macOS system trust | BLOCKED | `truststore` 0.10.4 reports `Russian Trusted Root CA` is not trusted; `/usr/bin/curl` reports the same issuer failure |
| TLS chain diagnostic | BLOCKED | OpenSSL verify return code 21 (`unable to verify the first certificate`); certificate body kept only in ignored local diagnostic file |
| Official CA source | BLOCKED | Official Gosuslugi source is `https://www.gosuslugi.ru/crt`, but access from this environment returns proxy `502 Bad Gateway`; no unverified certificate was installed |
| System Keychain CA | PASS | `Russian Trusted Root CA` is present with system trust settings; exported public certificate is valid through 2032 and marked `CA:TRUE` |
| System HTTPS | PASS | Direct `/usr/bin/curl` and Python `truststore` both receive an HTTP response from `zakupki.gov.ru` without proxy or TLS verification errors |
| Official-file comparison | BLOCKED | Keychain export SHA-256 `AA800EF345422D6158C6FAFE1C06C429DBDA21C3DF4BB1CCB45A920EC1111399` differs from the owner-downloaded 2025 root SHA-256 `5B51DB721B7C34958ED7432AE917A91297DD37508B2CAE4F858FFBAC6BC525EF` |
| Certificate identity method | PASS | `inspect-cert` now reports X.509 DER `certificate_sha256` as the primary identifier and raw `file_sha256` only as supplemental integrity data |
| Normalized certificate comparison | BLOCKED | Keychain DER SHA `D26D2D0231B7C39F92CC738512BA54103519E4405D68B5BD703E9788CA8ECF31` matches none of the downloaded root/intermediate DER fingerprints |
| ETP policy bootstrap | NOT RUN | Authority was not added because the fingerprint comparison failed |
| SOAP token | PASS | Protected env source reports configured; value was not printed |
| getDocsIP smoke | PASS | Known number `0352300080626000109`: SOAP `completed`, one archive URL, direct route, no proxy/TLS error |
| Public discovery | PASS WITH LIMIT | 9 candidates returned for 15.06.2026–15.07.2026; one failed validation with HTTP 404; one previously validated candidate retained |
| Validated frozen cases | PASS | 10 unique numbers; all getDocsIP completed and archives downloaded; no full analysis/report pre-run |
| Category distribution | PASS | 2 electrical_goods, 2 standard_goods, 2 services, 2 complex_or_incomplete, 2 additional |
| Backend health | PASS | `http://127.0.0.1:8001/health` returned 200 |
| Operator UI | PASS | `http://127.0.0.1:8001/demo/tender-agent` returned 401 without owner session, confirming protected UI route |
| EIS token setting | BLOCKED | Expected variable is `ZAKUPKI_GOV_RU_SOAP_TOKEN`; it is not configured in this environment |
| Frozen set of 10 unique procurements | NOT RUN | Cannot select or invent numbers without verified EIS results |
| Operator UI | NOT RUN | No valid case set is available for a session |
| Web/DOCX/PDF export | NOT RUN | No valid case set is available for a session |

System Keychain remains the TLS source for this session; the local ETP policy uses `macos_system` for the two exact EIS hosts. The trust manager uses DER certificate identity for explicit CA authorities. The validated case set is frozen in `operator_case_set.yaml`; selected cases were not sent through extraction, analysis, or report generation. No token, certificate, archive, or diagnostic file is tracked in Git.

## Verification

- `make check`: PASS
- focused tests: `63 passed, 1 warning`
- secret scan: PASS
- `docs/r3/operator_case_set.yaml`: not created; no candidate passed getDocsIP validation
- `docs/r3/operator_pilot_log.csv`: not created; there is no valid frozen set of ten cases
