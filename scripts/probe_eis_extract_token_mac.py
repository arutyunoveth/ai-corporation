from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import time
import uuid
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.eis_token_probe.read_secret_token import read_token_file
from src.tender_research.sync.eis_params import (
    format_eis_create_datetime,
    format_eis_exact_date,
    normalize_eis_region_code,
)

NS_SOAPENV = "http://schemas.xmlsoap.org/soap/envelope/"
NS_EIS = "http://zakupki.gov.ru/fz44/get-docs-ip/ws"
TOKEN_HEADER_NAME = "individualPerson_token"
SOAP_ACTION = "http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip"
CONTENT_TYPE = "text/xml; charset=utf-8"
USER_AGENT = "ArvectumTenderAgent/0.1 read-only"
MOSCOW_TZ = timezone(timedelta(hours=3))


def _redact_token(text: str) -> str:
    import re
    text = re.sub(
        r'(individualPerson_token[^>]*>)([^<]+)(</)',
        r'\1***REDACTED***\3',
        text,
    )
    text = re.sub(
        r'(<usertoken[^>]*>)([^<]+)(</)',
        r'\1***REDACTED***\3',
        text,
    )
    text = re.sub(r'(Authorization:\s*)(\S+)', r'\1***REDACTED***', text)
    text = re.sub(r'(Bearer\s+)(\S+)', r'\1***REDACTED***', text)
    text = re.sub(r'(individualPerson_token:\s*)(\S+)', r'\1***REDACTED***', text)
    return text


def _safe_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _make_envelope(body_xml: str, token: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{NS_SOAPENV}" xmlns:ws="{NS_EIS}">
  <soapenv:Header>
    <{TOKEN_HEADER_NAME}>{escape(token)}</{TOKEN_HEADER_NAME}>
  </soapenv:Header>
  <soapenv:Body>
    {body_xml}
  </soapenv:Body>
</soapenv:Envelope>"""


def _index_block(request_id: str, created_time: str) -> str:
    return f"""<index>
    <id>{escape(request_id)}</id>
    <createDateTime>{escape(created_time)}</createDateTime>
    <mode>PROD</mode>
  </index>"""


def _build_get_nsi_body(request_id: str, created_time: str) -> str:
    return f"""<ws:getNsiRequest>
  {_index_block(request_id, created_time)}
  <selectionParams>
    <nsiCode44>nsiAllList</nsiCode44>
    <nsiKind>all</nsiKind>
  </selectionParams>
</ws:getNsiRequest>"""


def _build_get_docs_by_org_region_body(
    request_id: str, created_time: str, region: str, exact_date: str,
) -> str:
    return f"""<ws:getDocsByOrgRegionRequest>
  {_index_block(request_id, created_time)}
  <selectionParams>
    <orgRegion>{escape(region)}</orgRegion>
    <subsystemType>PRIZ</subsystemType>
    <documentType44>epNotificationEF2020</documentType44>
    <periodInfo>
      <exactDate>{escape(exact_date)}</exactDate>
    </periodInfo>
  </selectionParams>
</ws:getDocsByOrgRegionRequest>"""


def _build_get_docs_by_reestr_number_body(
    request_id: str, created_time: str, reestr_number: str,
) -> str:
    return f"""<ws:getDocsByReestrNumberRequest>
  {_index_block(request_id, created_time)}
  <selectionParams>
    <subsystemType>PRIZ</subsystemType>
    <reestrNumber>{escape(reestr_number)}</reestrNumber>
  </selectionParams>
</ws:getDocsByReestrNumberRequest>"""


def _send_soap(
    envelope: str,
    endpoint: str,
    timeout: int = 30,
    allow_insecure: bool = False,
) -> dict[str, Any]:
    data = envelope.encode("utf-8")
    req = Request(
        endpoint,
        data=data,
        method="POST",
        headers={
            "Content-Type": CONTENT_TYPE,
            "SOAPAction": SOAP_ACTION,
            "User-Agent": USER_AGENT,
        },
    )
    ctx = ssl.create_default_context()
    if allow_insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    bypass_proxy = True
    try:
        opener = build_opener(
            HTTPSHandler(context=ctx),
            ProxyHandler({}) if bypass_proxy else ProxyHandler(),
        )
        resp = opener.open(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")
        return {"http_status": resp.status, "body": body, "error": None}
    except HTTPError as e:
        error_body = b""
        try:
            error_body = e.read()
        except Exception:
            pass
        return {
            "http_status": e.code,
            "body": error_body.decode("utf-8", errors="replace") if error_body else "",
            "error": f"HTTP {e.code}: {e.reason}",
        }
    except URLError as e:
        return {"http_status": 0, "body": "", "error": f"URLError: {e.reason}"}
    except Exception as e:
        return {"http_status": 0, "body": "", "error": f"{type(e).__name__}: {e}"}


def _classify_soap_response(
    result: dict[str, Any],
    operation: str,
    expected_response_tag: str,
) -> dict[str, Any]:
    classification = "unknown"
    application_code = None
    archive_urls: list[str] = []
    sanitized_message = ""
    fault_code = None
    fault_string = None

    if result.get("error"):
        if "URL" in result["error"] or "timed out" in result["error"]:
            classification = "transport_error"
        else:
            classification = "transport_error"
        sanitized_message = _redact_token(result["error"])
    elif result.get("http_status", 0) != 200:
        classification = "HTTP_error"
        sanitized_message = _redact_token(result.get("body", ""))[:500]
    else:
        body = result.get("body", "")
        if "<soapenv:Fault>" in body or "<soap:Fault>" in body:
            classification = "SOAP_fault"
            try:
                root = ET.fromstring(body.encode("utf-8"))
                ns = {"soapenv": NS_SOAPENV, "soap": NS_SOAPENV}
                for fault in root.iter("{http://schemas.xmlsoap.org/soap/envelope/}Fault"):
                    fc = fault.find("faultcode")
                    fs = fault.find("faultstring")
                    if fc is not None and fc.text:
                        fault_code = fc.text
                    if fs is not None and fs.text:
                        fault_string = fs.text
                        if "code=5" in fs.text:
                            classification = "token_rejected"
                        elif "code=" in fs.text:
                            classification = "authorization_error"
                        elif "not found" in fs.text.lower():
                            classification = "validation_error"
                        else:
                            classification = "SOAP_fault"
                    sanitized_message = _redact_token(body)[:1000]
            except Exception:
                sanitized_message = _redact_token(body)[:500]
        else:
            classification = "accepted"
            try:
                root = ET.fromstring(body.encode("utf-8"))
                ns_map = {
                    "soapenv": NS_SOAPENV,
                    "ws": NS_EIS,
                }
                for elem in root.iter():
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    if tag == "archiveUrl" and elem.text:
                        archive_urls.append(elem.text.strip())
                    elif tag == "code" and elem.text:
                        application_code = elem.text.strip()
                if expected_response_tag in body:
                    classification = "accepted"
                    if archive_urls:
                        classification = "archive_url_received"
                else:
                    if not archive_urls:
                        classification = "empty_success"
                sanitized_message = _redact_token(body)[:1000]
            except Exception:
                sanitized_message = _redact_token(body)[:500]

    return {
        "classification": classification,
        "application_code": application_code,
        "archive_urls": archive_urls,
        "fault_code": fault_code,
        "fault_string": fault_string,
        "sanitized_message": sanitized_message[:5000],
    }


def _http_download_head(
    url: str,
    token: str | None,
    timeout: int = 15,
    allow_insecure: bool = False,
) -> dict[str, Any]:
    headers = {
        "User-Agent": USER_AGENT,
    }
    if token is not None:
        headers[TOKEN_HEADER_NAME] = token

    req = Request(url, method="HEAD", headers=headers)
    ctx = ssl.create_default_context()
    if allow_insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        opener = build_opener(
            HTTPSHandler(context=ctx),
            ProxyHandler({}),
        )
        resp = opener.open(req, timeout=timeout)
        content_type = resp.headers.get("Content-Type", "")
        content_length = resp.headers.get("Content-Length", "")
        return {
            "http_status": resp.status,
            "content_type": content_type,
            "content_length": content_length,
            "error": None,
        }
    except HTTPError as e:
        return {
            "http_status": e.code,
            "content_type": "",
            "content_length": "",
            "error": f"HTTP {e.code}: {e.reason}",
        }
    except Exception as e:
        return {
            "http_status": 0,
            "content_type": "",
            "content_length": "",
            "error": f"{type(e).__name__}: {e}",
        }


def _http_download_get_first_bytes(
    url: str,
    token: str | None,
    max_bytes: int = 1024,
    timeout: int = 15,
    allow_insecure: bool = False,
) -> dict[str, Any]:
    headers = {
        "User-Agent": USER_AGENT,
        "Range": f"bytes=0-{max_bytes - 1}",
    }
    if token is not None:
        headers[TOKEN_HEADER_NAME] = token

    req = Request(url, headers=headers)
    ctx = ssl.create_default_context()
    if allow_insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        opener = build_opener(
            HTTPSHandler(context=ctx),
            ProxyHandler({}),
        )
        resp = opener.open(req, timeout=timeout)
        data = resp.read(max_bytes)
        content_type = resp.headers.get("Content-Type", "")
        is_zip = data[:2] == b"PK" if len(data) >= 2 else False
        return {
            "http_status": resp.status,
            "content_type": content_type,
            "bytes_received": len(data),
            "zip_signature": is_zip,
            "error": None,
        }
    except HTTPError as e:
        error_body = b""
        try:
            error_body = e.read(max_bytes)
        except Exception:
            pass
        return {
            "http_status": e.code,
            "content_type": "",
            "bytes_received": len(error_body),
            "zip_signature": False,
            "error": f"HTTP {e.code}: {e.reason}",
        }
    except Exception as e:
        return {
            "http_status": 0,
            "content_type": "",
            "bytes_received": 0,
            "zip_signature": False,
            "error": f"{type(e).__name__}: {e}",
        }


def probe_operation(
    operation: str,
    body_builder,
    expected_response_tag: str,
    token_value: str | None,
    endpoint: str,
    allow_insecure: bool,
    output_dir: Path,
    request_id: str,
    created_time: str,
    **kwargs: Any,
) -> dict[str, Any]:
    if token_value is None:
        token_used = ""
    else:
        token_used = token_value

    body_xml = body_builder(request_id, created_time, **kwargs)
    envelope = _make_envelope(body_xml, token_used)

    start = time.monotonic()
    raw_result = _send_soap(envelope, endpoint, allow_insecure=allow_insecure)
    elapsed = time.monotonic() - start

    classified = _classify_soap_response(raw_result, operation, expected_response_tag)

    return {
        "operation": operation,
        "request_id": request_id,
        "http_status": raw_result.get("http_status"),
        "transport_error": raw_result.get("error"),
        "elapsed_ms": round(elapsed * 1000),
        **classified,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EIS Document Export Token Probe (macOS, no Rutoken)",
    )
    parser.add_argument(
        "--token-file",
        default="~/Desktop/SOAP-extract.txt",
        help="Path to new extract token file",
    )
    parser.add_argument(
        "--endpoint",
        default="https://int.zakupki.gov.ru/eis-integration/services/getDocsIP",
        help="GetDocsIP endpoint URL",
    )
    parser.add_argument(
        "--operation",
        default="getNsi",
        choices=["getNsi", "getDocsByOrgRegion", "getDocsByReestrNumber"],
        help="Operation to test",
    )
    parser.add_argument(
        "--output-dir",
        default="tmp/eis_extract_token_mac",
        help="Output directory for reports",
    )
    parser.add_argument(
        "--allow-insecure-development-tls",
        action="store_true",
        help="Allow insecure TLS (CERT_NONE) for stunnel/dev",
    )
    parser.add_argument(
        "--purchase-number",
        default="0372200263426001094",
        help="Reestr number for getDocsByReestrNumber",
    )
    parser.add_argument(
        "--region",
        default="77",
        help="KLADR region code",
    )
    parser.add_argument(
        "--exact-date",
        default=None,
        help="Exact date with timezone (default: yesterday Moscow time)",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "probe_results.json"
    md_path = output_dir / "probe_results.md"

    individual_token = os.environ.get("ZAKUPKI_GOV_RU_SOAP_TOKEN") or ""
    is_individual_configured = bool(individual_token)

    meta = read_token_file(args.token_file)
    new_extract_token = meta.normalized
    extract_fingerprint = meta.sha256
    meta.clear()

    invalid_token = str(uuid.uuid4())

    yesterday = date.today() - timedelta(days=1)
    if args.exact_date:
        exact_date = format_eis_exact_date(args.exact_date)
    else:
        exact_date = format_eis_exact_date(yesterday, timezone="Europe/Moscow")

    region = normalize_eis_region_code(args.region) if args.region else "77"

    credential_modes: list[tuple[str, str | None, str]] = [
        ("no_token", None, "none"),
        ("invalid_random_token", invalid_token, _safe_sha256(invalid_token)),
        ("new_extract_token", new_extract_token, extract_fingerprint),
    ]
    if is_individual_configured:
        credential_modes.append(
            ("existing_individual_token", individual_token, _safe_sha256(individual_token))
        )

    operation = args.operation
    body_builder = None
    expected_tag = ""

    if operation == "getNsi":
        body_builder = _build_get_nsi_body
        expected_tag = "getNsiResponse"
    elif operation == "getDocsByOrgRegion":
        body_builder = _build_get_docs_by_org_region_body
        expected_tag = "getDocsByOrgRegionResponse"
    elif operation == "getDocsByReestrNumber":
        body_builder = _build_get_docs_by_reestr_number_body
        expected_tag = "getDocsByReestrNumberResponse"

    all_results: list[dict[str, Any]] = []
    for mode_name, token_val, fp in credential_modes:
        rid = str(uuid.uuid4())
        ctime = format_eis_create_datetime(datetime.now(UTC))

        probe_kwargs = {}
        if operation == "getDocsByOrgRegion":
            probe_kwargs["region"] = region
            probe_kwargs["exact_date"] = exact_date
        elif operation == "getDocsByReestrNumber":
            probe_kwargs["reestr_number"] = args.purchase_number

        result = probe_operation(
            operation=operation,
            body_builder=body_builder,
            expected_response_tag=expected_tag,
            token_value=token_val,
            endpoint=args.endpoint,
            allow_insecure=args.allow_insecure_development_tls,
            output_dir=output_dir,
            request_id=rid,
            created_time=ctime,
            **probe_kwargs,
        )

        result["credential_mode"] = mode_name
        result["token_fingerprint_sha256"] = fp
        result["endpoint"] = args.endpoint
        result["transport"] = "stunnel" if "127.0.0.1" in args.endpoint else "direct"
        all_results.append(result)

    # ── Download probe (if archive URLs were received) ──
    download_results: list[dict[str, Any]] = []
    for res in all_results:
        if res.get("archive_urls") and len(res["archive_urls"]) > 0:
            url = res["archive_urls"][0]
            url_fingerprint = _safe_sha256(url)

            for dlmode_name, dl_token_val in [
                ("no_token", None),
                ("invalid_random_token", str(uuid.uuid4())),
                ("new_extract_token", new_extract_token),
            ] + ([("existing_individual_token", individual_token)] if is_individual_configured else []):
                dl_result = _http_download_get_first_bytes(
                    url,
                    dl_token_val,
                    allow_insecure=args.allow_insecure_development_tls,
                )
                dl_result["credential_mode"] = dlmode_name
                dl_result["url_fingerprint_sha256"] = url_fingerprint
                dl_result["token_fingerprint_sha256"] = (
                    _safe_sha256(dl_token_val) if dl_token_val else "none"
                )
                download_results.append(dl_result)
            break

    # ── Summary ──
    summary = {
        "platform": "macos",
        "rutoken_used": False,
        "client_certificate_used": False,
        "windows_gateway_used": False,
        "endpoint": args.endpoint,
        "allow_insecure_tls": args.allow_insecure_development_tls,
        "operation": operation,
        "region": region,
        "exact_date": exact_date,
        "purchase_number": args.purchase_number,
        "individual_token_configured": is_individual_configured,
        "credential_modes_tested": [m[0] for m in credential_modes],
        "soap_results": all_results,
        "download_results": download_results,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# EIS Extract Token Probe — {operation}\n\n")
        f.write(f"**Platform:** macOS | **Rutoken:** no | **Windows Gateway:** no\n\n")
        f.write(f"**Endpoint:** `{args.endpoint}`\n\n")
        f.write(f"**Allow Insecure TLS:** {args.allow_insecure_development_tls}\n\n")
        f.write(f"## SOAP Results\n\n")
        f.write("| Mode | HTTP Status | Classification | App Code | Archive URLs | Fault |\n")
        f.write("|------|------------|---------------|----------|-------------|-------|\n")
        for r in all_results:
            f.write(
                f"| {r['credential_mode']} "
                f"| {r.get('http_status', 'N/A')} "
                f"| {r.get('classification', 'N/A')} "
                f"| {r.get('application_code', 'N/A')} "
                f"| {len(r.get('archive_urls', []))} "
                f"| {r.get('fault_string', 'N/A')[:60] if r.get('fault_string') else 'N/A'} "
                f"|\n"
            )
        f.write("\n")

        if download_results:
            f.write("## Download Results\n\n")
            f.write("| Mode | HTTP Status | Content-Type | ZIP Signature | Error |\n")
            f.write("|------|------------|-------------|--------------|-------|\n")
            for d in download_results:
                f.write(
                    f"| {d['credential_mode']} "
                    f"| {d.get('http_status', 'N/A')} "
                    f"| {d.get('content_type', 'N/A')[:40]} "
                    f"| {d.get('zip_signature', False)} "
                    f"| {d.get('error', 'N/A')[:60] if d.get('error') else 'N/A'} "
                    f"|\n"
                )
            f.write("\n")

    print(f"Results saved to {report_path}")
    print(f"Report saved to {md_path}")

    for r in all_results:
        cls = r.get("classification", "unknown")
        mode = r["credential_mode"]
        http_status_str = str(r.get('http_status', '?'))
        print(f"  {mode:40s} → HTTP {http_status_str:>3s} | {cls:25s} | arch={len(r.get('archive_urls',[]))}")

    if download_results:
        print("\nDownload matrix:")
        for d in download_results:
            zip_ok = "ZIP" if d.get("zip_signature") else "no ZIP"
            dl_http = str(d.get('http_status', '?'))
        print(f"  {d['credential_mode']:40s} → HTTP {dl_http:>3s} | {zip_ok}")


if __name__ == "__main__":
    main()
