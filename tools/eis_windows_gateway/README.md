# EIS services-vbs Windows GOST Gateway

This folder contains reusable, secret-free diagnostics and local gateway helpers for testing EIS `services-vbs` through a Windows machine with CryptoPro/Rutoken GOST TLS support.

Security rules:

- Do not put PIN values in scripts, configs, logs, command lines, or chat.
- Do not export Rutoken private keys or certificate containers.
- Keep all listeners bound to `127.0.0.1`.
- Keep local configs under `tools/eis_windows_gateway/local/` or `%USERPROFILE%\Arvectum\EisServicesVbsTest\config`; both are local-only.
- Legal token stays on the Mac side and is sent through the SSH tunnel only in SOAP requests.

Expected topology:

```text
Mac SOAP client -> 127.0.0.1:18110 -> SSH -> Windows 127.0.0.1:8110 -> CryptoPro Stunnel -> int44.zakupki.gov.ru:443
```

If a client certificate is required, use the certificate gateway variant on Windows only after the server/gateway explicitly reports certificate requirement. The PIN must be entered only in the local Windows UI prompt.

Current blocker captured by diagnostics: CryptoPro CSP and Rutoken containers are present, but CryptoPro Stunnel was not found in the standard CryptoPro installation directories or `PATH`.
