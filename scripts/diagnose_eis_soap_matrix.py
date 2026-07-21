#!/usr/bin/env python3
"""
EIS SOAP Endpoint/Token Matrix Diagnostic.

Checks DOCS (getDocsIP) and SEARCH (services-vbs) capabilities
with individual and legal entity tokens across candidate endpoints.

Usage:
    python scripts/diagnose_eis_soap_matrix.py --query "кабель" --limit 1
    python scripts/diagnose_eis_soap_matrix.py --query "кабель" --limit 1 --output /tmp/eis_report

Output:
    tmp/eis_soap_matrix_report.json
    tmp/eis_soap_matrix_report.md
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener
from uuid import uuid4
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
LEGACY_ZAKUPKI_NS = "http://zakupki.gov.ru/eis-integration/services-vbs"
GETDOCS_NS = "http://zakupki.gov.ru/fz44/get-docs-ip/ws"

DEFAULT_TIMEOUT = 20

ENDPOINT_CANDIDATES = [
    ("int-getdocsip", "https://int.zakupki.gov.ru/eis-integration/services/getDocsIP", ["docs"]),
    ("int-services-vbs", "https://int.zakupki.gov.ru/eis-integration/services-vbs", ["search"]),
    ("int-services-vbs-wsdl", "https://int.zakupki.gov.ru/eis-integration/services-vbs?wsdl", ["search"]),
    ("int44-ttls-services-vbs", "https://int44-ttls-cert.zakupki.gov.ru/eis-integration/services-vbs", ["search"]),
    ("int44-ttls-services-vbs-wsdl", "https://int44-ttls-cert.zakupki.gov.ru/eis-integration/services-vbs?wsdl", ["search"]),
    ("int44-legacy-services-vbs", "https://int44.zakupki.gov.ru/eis-integration/services-vbs", ["search"]),
]

PROCUREMENT_NUMBERS = [
    "0373100000124000001",
    "0373100127724000258",
    "0373100000125000001",
]


@dataclass
class ProbeResult:
    capability: str = ""
    endpoint_name: str = ""
    endpoint_url: str = ""
    token_type: str = ""
    token_fingerprint: str = ""
    transport_status: str = "unknown"
    http_status: int | None = None
    soap_status: str = "not_checked"
    error_class: str = ""
    sanitized_error: str = ""
    elapsed_ms: int = 0
    conclusion: str = "unknown"


def fingerprint(token: str) -> str:
    t = token.strip()
    if not t or len(t) < 8:
        return t[:4] if t else "none"
    return f"{t[:4]}...{t[-4:]}"


def _build_opener():
    from src.shared.network.etp_trust import build_ssl_context, policy_from_environment
    ctx = build_ssl_context("int.zakupki.gov.ru", policy_from_environment())
    return build_opener(HTTPSHandler(context=ctx), ProxyHandler({}))


def _sanitize(msg: str) -> str:
    for key in ("ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN", "ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN", "ZAKUPKI_GOV_RU_SOAP_TOKEN"):
        val = os.environ.get(key, "")
        if val and val in msg:
            msg = msg.replace(val, "[redacted]")
    return msg


def classify_transport_error(e: Exception) -> tuple[str, str]:
    if isinstance(e, HTTPError):
        return "http_error", f"HTTP {e.code}"
    msg = str(e)
    if isinstance(e, URLError):
        reason = str(e.reason) if hasattr(e, "reason") else msg
        rl = reason.lower()
        if "timed out" in rl or "timeout" in rl:
            return "timeout", reason
        if "connection reset" in rl:
            return "tls_reset", reason
        if "handshake failure" in rl:
            return "handshake_failure", reason
        if ("name" in rl and ("service" in rl or "known" in rl)) or "nodename" in rl:
            return "dns_error", reason
        if "connection refused" in rl or "connection aborted" in rl:
            return "tcp_error", reason
        return "unknown", reason
    if isinstance(e, ConnectionResetError):
        return "tls_reset", str(e)
    if isinstance(e, TimeoutError):
        return "timeout", str(e)
    return "unknown", str(e)


def probe_url(url: str, method: str = "GET", data: bytes | None = None, headers: dict | None = None,
              timeout: int = DEFAULT_TIMEOUT) -> tuple[str, int | None, str, str, bytes | None]:
    start = time.monotonic()
    opener = _build_opener()
    req = Request(url, data=data, method=method)
    req.add_header("User-Agent", "EIS-Diagnostic/1.0")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(200 * 1024)
            elapsed = int((time.monotonic() - start) * 1000)
            return "tls_ok", resp.status, "", "", body
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        ts, err_msg = classify_transport_error(e)
        ec = type(e).__name__
        http_code = e.code if isinstance(e, HTTPError) else None
        return ts, http_code, ec, _sanitize(err_msg), None


def probe_wsdl(url: str) -> ProbeResult:
    r = ProbeResult(endpoint_url=url)
    ts, http, ec, err, body = probe_url(url)
    r.transport_status = ts
    r.http_status = http
    r.error_class = ec
    r.sanitized_error = err
    if ts == "tls_ok" and body:
        if b"<xs:schema" in body or b"<wsdl:definitions" in body or b"<xsd:schema" in body:
            r.soap_status = "wsdl_loaded"
        else:
            r.soap_status = "invalid_response"
    return r


def probe_soap_post(url: str, envelope: str, soap_action: str | None) -> ProbeResult:
    r = ProbeResult(endpoint_url=url)
    headers = {"Content-Type": "text/xml; charset=utf-8"}
    if soap_action:
        headers["SOAPAction"] = soap_action
    ts, http, ec, err, body = probe_url(url, method="POST", data=envelope.encode("utf-8"), headers=headers)
    r.transport_status = ts
    r.http_status = http
    r.error_class = ec
    r.sanitized_error = err
    if ts == "tls_ok" and body:
        xml = body.decode("utf-8", errors="replace")
        if "<soap:Fault>" in xml or "<faultstring>" in xml:
            r.soap_status = "soap_fault"
        elif "noData>true" in xml:
            r.soap_status = "soap_ok"
        elif "archiveUrl" in xml or "ArchiveInfo" in xml:
            r.soap_status = "soap_ok"
        elif "searchProcurementsResponse" in xml or "<procurement" in xml.lower():
            r.soap_status = "soap_ok"
        elif "errorInfo" in xml:
            r.soap_status = "invalid_request"
        else:
            r.soap_status = "soap_ok"
    return r


def build_docs_envelope(token: str, reestr_number: str) -> str:
    rid = str(uuid4())
    ctime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:ws="{GETDOCS_NS}">
  <soapenv:Header>
    <individualPerson_token>{escape(token)}</individualPerson_token>
  </soapenv:Header>
  <soapenv:Body>
    <ws:getDocsByReestrNumberRequest>
      <index>
        <id>{escape(rid)}</id>
        <createDateTime>{escape(ctime)}</createDateTime>
        <mode>PROD</mode>
      </index>
      <selectionParams>
        <subsystemType>PRIZ</subsystemType>
        <reestrNumber>{escape(reestr_number)}</reestrNumber>
      </selectionParams>
    </ws:getDocsByReestrNumberRequest>
  </soapenv:Body>
</soapenv:Envelope>"""


def build_search_envelope(token: str, query: str, limit: int = 3) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:zak="{LEGACY_ZAKUPKI_NS}">
  <soapenv:Header>
    <zak:usertoken>{escape(token)}</zak:usertoken>
  </soapenv:Header>
  <soapenv:Body>
    <zak:searchProcurements>
      <zak:query>{escape(query)}</zak:query>
      <zak:maxResults>{limit}</zak:maxResults>
    </zak:searchProcurements>
  </soapenv:Body>
</soapenv:Envelope>"""


def conclude(r: ProbeResult) -> str:
    if r.transport_status == "tls_ok":
        if r.soap_status in ("soap_ok", "wsdl_loaded"):
            return "usable_without_rutoken"
        if r.soap_status == "soap_fault":
            return "token_rejected"
        if r.http_status in (401, 403):
            return "token_rejected"
        return "soap_xml_problem"
    if r.transport_status in ("tls_reset", "handshake_failure"):
        return "requires_gost_gateway"
    return "endpoint_unavailable"


def _load_env():
    root = Path(__file__).resolve().parents[1]
    for env_file in (root / ".env", root / ".env.local"):
        if not env_file.is_file():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def run_matrix(query: str = "кабель", limit: int = 1) -> list[ProbeResult]:
    _load_env()
    individual_token = os.environ.get("ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN") or os.environ.get("ZAKUPKI_GOV_RU_SOAP_TOKEN", "")
    legal_token = os.environ.get("ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN", "")
    all_results: list[ProbeResult] = []

    for name, url, capabilities in ENDPOINT_CANDIDATES:
        for cap in capabilities:
            if cap == "docs":
                for token_type, token in [("individual", individual_token)]:
                    if not token.strip():
                        continue
                    envelope = build_docs_envelope(token, PROCUREMENT_NUMBERS[0])
                    soap_r = probe_soap_post(url, envelope, "http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip")
                    soap_r.capability = "docs"
                    soap_r.endpoint_name = name
                    soap_r.token_type = token_type
                    soap_r.token_fingerprint = fingerprint(token)
                    soap_r.conclusion = conclude(soap_r)
                    all_results.append(soap_r)
            elif cap == "search":
                for token_type, token in [("individual", individual_token), ("legal_entity", legal_token)]:
                    if not token.strip():
                        continue
                    # WSDL probe first
                    wsdl_r = probe_wsdl(url)
                    wsdl_r.capability = "search"
                    wsdl_r.endpoint_name = name
                    wsdl_r.token_type = token_type
                    wsdl_r.token_fingerprint = fingerprint(token)
                    wsdl_r.conclusion = conclude(wsdl_r)
                    all_results.append(wsdl_r)

                    # SOAP POST
                    envelope = build_search_envelope(token, query, limit)
                    soap_r = probe_soap_post(url, envelope, "searchProcurements")
                    soap_r.capability = "search"
                    soap_r.endpoint_name = name
                    soap_r.token_type = token_type
                    soap_r.token_fingerprint = fingerprint(token)
                    soap_r.conclusion = conclude(soap_r)
                    all_results.append(soap_r)

    return all_results


def results_to_json(results: list[ProbeResult]) -> dict[str, Any]:
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "environment": {
            "hostname": os.uname().nodename,
            "platform": sys.platform,
        },
        "probes": [asdict(r) for r in results],
        "summary": {
            "total": len(results),
            "usable_without_rutoken": sum(1 for r in results if r.conclusion == "usable_without_rutoken"),
            "token_rejected": sum(1 for r in results if r.conclusion == "token_rejected"),
            "requires_gost_gateway": sum(1 for r in results if r.conclusion == "requires_gost_gateway"),
            "endpoint_unavailable": sum(1 for r in results if r.conclusion == "endpoint_unavailable"),
            "soap_xml_problem": sum(1 for r in results if r.conclusion == "soap_xml_problem"),
        },
    }


def render_md_report(results: list[ProbeResult], path: Path) -> None:
    lines = [
        "# EIS SOAP Matrix Diagnostic Report",
        f"\n**Generated:** {datetime.utcnow().isoformat()}",
        f"**Host:** {os.uname().nodename}  ",
        f"**Platform:** {sys.platform}  ",
        "\n## Summary",
        "| Status | Count |",
        "|--------|-------|",
    ]
    summary = {}
    for r in results:
        summary[r.conclusion] = summary.get(r.conclusion, 0) + 1
    for st, cnt in sorted(summary.items()):
        lines.append(f"| {st} | {cnt} |")

    lines.append("\n## Probe Matrix\n")
    lines.append("| capability | endpoint | token | transport | http | soap | conclusion |")
    lines.append("|-----------|----------|-------|-----------|------|------|------------|")
    icons = {"tls_ok": "✅", "tls_reset": "❌", "handshake_failure": "❌", "dns_error": "❌",
             "tcp_error": "❌", "timeout": "⏱", "http_error": "⚠", "unknown": "❓"}
    for r in results:
        icon = icons.get(r.transport_status, "❓")
        http_s = str(r.http_status) if r.http_status else "—"
        lines.append(
            f"| {r.capability} | {r.endpoint_name} | {r.token_fingerprint} "
            f"| {icon}{r.transport_status} | {http_s} | {r.soap_status} | {r.conclusion} |"
        )

    has_gost = any(r.conclusion == "requires_gost_gateway" for r in results)
    has_usable = any(r.conclusion == "usable_without_rutoken" for r in results)
    lines.append("\n## Recommendations\n")
    if has_usable:
        lines.append("- ✅ **Есть рабочие endpoint'ы без Рутокена (getDocsIP).**")
    if has_gost:
        lines.append("- ❌ **services-vbs не работает напрямую на macOS/OpenSSL — требуется ГОСТ-шлюз.**")
    lines.append("- getDocsIP на int.zakupki.gov.ru работает с individual token без Рутокена.")
    lines.append("- services-vbs на int44*.zakupki.gov.ru сбрасывает TLS — нужен gateway с КриптоПро.")
    lines.append("- Для production рекомендован gateway: EIS_SOAP_SEARCH_TRANSPORT=gateway")

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="EIS SOAP Matrix Diagnostic")
    parser.add_argument("--query", default="кабель")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--output", default="tmp")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("EIS SOAP Matrix Diagnostic")
    print(f"Query: {args.query}  Limit: {args.limit}")

    results = run_matrix(query=args.query, limit=args.limit)

    report = results_to_json(results)
    jp = out_dir / "eis_soap_matrix_report.json"
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON: {jp}")

    mp = out_dir / "eis_soap_matrix_report.md"
    render_md_report(results, mp)
    print(f"MD:   {mp}")

    print("\nSummary:")
    for st, cnt in report["summary"].items():
        if isinstance(cnt, int):
            print(f"  {st}: {cnt}")

    usable = [r for r in results if r.conclusion == "usable_without_rutoken"]
    if usable:
        print("\nUsable without rutoken:")
        for r in usable:
            print(f"  {r.capability} @ {r.endpoint_name} ({r.token_type})")
    else:
        print("\nNo usable endpoints without rutoken.")


if __name__ == "__main__":
    main()
