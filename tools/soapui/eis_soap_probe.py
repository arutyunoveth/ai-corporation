#!/usr/bin/env python3
"""SOAP probe for EIS getDocsIP (all 5 operations) via stunnel.

Usage:
    python3 tools/soapui/eis_soap_probe.py [--token TOKEN] [--reestr NUM] [--endpoint URL]

Environment:
    EIS_INDIVIDUAL_TOKEN  — individual token (default: probes with placeholder)
    REESTR_NUMBER         — reestr number (default: 0994800000725000013)
    STUNNEL_ENDPOINT      — stunnel URL (default: http://127.0.0.1:8099)
"""

import os, sys, uuid, json, textwrap, re
from datetime import datetime, timezone, timedelta
from xml.sax.saxutils import escape
from urllib.parse import urlparse

try:
    import urllib.request as urlreq
    import urllib.error as urlerror
    import ssl
except ImportError:
    urlreq = None
    urlerror = None
    ssl = None

MOSCOW_TZ = timezone(timedelta(hours=3))
NS_SOAPENV = "http://schemas.xmlsoap.org/soap/envelope/"
NS_EIS = "http://zakupki.gov.ru/fz44/get-docs-ip/ws"
TOKEN_HEADER = "individualPerson_token"
DEFAULT_ENDPOINT = "http://127.0.0.1:8099/eis-integration/services/getDocsIP"


def _build_envelope(body_xml: str, token: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{NS_SOAPENV}" xmlns:ws="{NS_EIS}">
  <soapenv:Header>
    <{TOKEN_HEADER}>{escape(token)}</{TOKEN_HEADER}>
  </soapenv:Header>
  <soapenv:Body>
    {body_xml}
  </soapenv:Body>
</soapenv:Envelope>"""


def _index_block(req_id: str) -> str:
    now = datetime.now(MOSCOW_TZ).isoformat()
    return f"""<index>
        <id>{escape(req_id)}</id>
        <createDateTime>{escape(now)}</createDateTime>
        <mode>{escape(mode)}</mode>PROD</mode>
      </index>"""


def _send(envelope: str, endpoint: str, timeout: int = 30) -> dict:
    """Send SOAP envelope via direct HTTPS (proxy bypass for EIS hosts)."""
    data = envelope.encode("utf-8")
    hostname = urlparse(endpoint).hostname or ""
    req = urlreq.Request(
        endpoint, data=data, method="POST",
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip",
        },
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    # Bypass proxy for EIS hosts (same as Python code)
    bypass_proxy = any(h in hostname for h in ["zakupki.gov.ru", "127.0.0.1"])
    try:
        if bypass_proxy:
            opener = urlreq.build_opener(
                urlreq.HTTPSHandler(context=ctx),
                urlreq.ProxyHandler({}),
            )
            resp = opener.open(req, timeout=timeout)
        else:
            resp = urlreq.urlopen(req, context=ctx, timeout=timeout)
        body = resp.read().decode("utf-8")
        return {"http_status": resp.status, "body": body, "error": None}
    except urlerror.HTTPError as e:
        return {"http_status": e.code, "body": "", "error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"http_status": 0, "body": "", "error": str(e)}


# ── Operation builders ────────────────────────────────────────────────

def op_get_docs_by_reestr_number(reestr_number: str, token: str) -> str:
    return _build_envelope(f"""<ws:getDocsByReestrNumberRequest>
      {_index_block("prb-rn-001")}
      <selectionParams>
        <subsystemType>PRIZ</subsystemType>
        <reestrNumber>{escape(reestr_number)}</reestrNumber>
      </selectionParams>
    </ws:getDocsByReestrNumberRequest>""", token)


def op_get_nsi(token: str) -> str:
    return _build_envelope(f"""<ws:getNsiRequest>
      {_index_block("prb-nsi-001")}
      <selectionParams>
        <nsiCode44>nsiAllList</nsiCode44>
        <nsiKind>all</nsiKind>
      </selectionParams>
    </ws:getNsiRequest>""", token)


def op_get_docs_by_org_region(token: str) -> str:
    return _build_envelope(f"""<ws:getDocsByOrgRegionRequest>
      {_index_block("prb-reg-001")}
      <selectionParams>
        <orgRegion>770000000000</orgRegion>
        <subsystemType>PRIZ</subsystemType>
        <documentType44>all</documentType44>
        <periodInfo>
          <exactDate>{datetime.now(MOSCOW_TZ).strftime("%Y-%m-%d")}</exactDate>
        </periodInfo>
      </selectionParams>
    </ws:getDocsByOrgRegionRequest>""", token)


def op_get_doc_signatures_by_url(token: str) -> str:
    return _build_envelope(f"""<ws:getDocSignaturesByUrlRequest>
      {_index_block("prb-sig-001")}
      <selectionParams>
        <signatureUrl>https://example.com/test-signature-url</signatureUrl>
      </selectionParams>
    </ws:getDocSignaturesByUrlRequest>""", token)


def op_get_prepared_part(token: str) -> str:
    return _build_envelope(f"""<ws:getPreparedPartRequest>
      {_index_block("prb-part-001")}
      <selectionParams>
        <partUrl>https://example.com/test-part-url</partUrl>
      </selectionParams>
    </ws:getPreparedPartRequest>""", token)


# ── Report ────────────────────────────────────────────────────────────

OPERATIONS = [
    ("getDocsByReestrNumber", op_get_docs_by_reestr_number,
     "Запрос архива документации по реестровому номеру"),
    ("getNsi", op_get_nsi,
     "Запрос справочников ЕИС (nsiAllList)"),
    ("getDocsByOrgRegion", op_get_docs_by_org_region,
     "Запрос документации по региону (Москва)"),
    ("getDocSignaturesByUrl", op_get_doc_signatures_by_url,
     "Запрос подписей по URL документа"),
    ("getPreparedPart", op_get_prepared_part,
     "Запрос подготовленной части по URL"),
]


def main():
    token = (os.environ.get("EIS_INDIVIDUAL_TOKEN")
             or os.environ.get("ZAKUPKI_GOV_RU_SOAP_TOKEN")
             or os.environ.get("ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN")
             or (sys.argv[sys.argv.index("--token") + 1] if "--token" in sys.argv else None)
             or "PLACEHOLDER_TOKEN")
    reestr = sys.argv[sys.argv.index("--reestr") + 1] if "--reestr" in sys.argv else (os.environ.get("REESTR_NUMBER") or "0994800000725000013")
    endpoint = sys.argv[sys.argv.index("--endpoint") + 1] if "--endpoint" in sys.argv else (os.environ.get("STUNNEL_ENDPOINT") or DEFAULT_ENDPOINT)

    if urlreq is None:
        print("FATAL: urllib not available. Python 3 required.")
        sys.exit(1)

    print(f"{'='*72}")
    print(f"  EIS SOAP Probe — getDocsIP (all 5 operations)")
    print(f"  Endpoint: {endpoint}")
    print(f"  Token present: {'YES' if token and token != 'PLACEHOLDER_TOKEN' else 'PLACEHOLDER (no real call)'}")
    print(f"  Reestr: {reestr}")
    print(f"  Timestamp: {datetime.now(MOSCOW_TZ).isoformat()}")
    print(f"{'='*72}")

    results = []
    for name, builder, desc in OPERATIONS:
        print(f"\n  ── {name} ──")
        print(f"     {desc}")

        envelope = builder(reestr, token) if name == "getDocsByReestrNumber" else builder(token)

        # Log envelope (redact token)
        safe_env = envelope.replace(token, "[REDACTED]") if token else envelope
        with open(f"/tmp/soapui_probe_{name}_request.xml", "w") as f:
            f.write(safe_env)
        print(f"     Envelope written: /tmp/soapui_probe_{name}_request.xml")

        if not token or token == "PLACEHOLDER_TOKEN":
            print(f"     ⚠ SKIP — placeholder token, no real call attempted")
            results.append({"operation": name, "status": "SKIPPED", "http": 0, "error": "placeholder token"})
            continue

        result = _send(envelope, endpoint)
        http = result["http_status"]
        error = result["error"]
        body = result["body"]

        if error:
            print(f"     ✗ ERROR: {error[:200]}")
            results.append({"operation": name, "status": "ERROR", "http": http, "error": error})
        else:
            # Parse EIS response format
            has_fault = "<soapenv:Fault>" in body or "<SOAP-ENV:Fault>" in body or "<Fault>" in body
            has_archive = "<archiveUrl>" in body or "archiveUrl" in body
            has_nsi_data = bool(re.search(r"<(nsi|nsiCode|nsiKind)", body))
            has_no_data = "noData" in body and ("true" in body.split("noData")[1][:20])
            has_error_info = "<errorInfo>" in body
            found_code = re.search(r"<code>(\d+)</code>", body)
            found_message = re.search(r"<message[^>]*>(.*?)</message>", body, re.DOTALL)
            is_bus_ack = "<bus:parameters>" in body or "<parameters>" in body
            is_eis_response = bool(re.search(r"<(getDocsByReestrNumberResponse|getNsiResponse|getDocsByOrgRegionResponse|getDocSignaturesByUrlResponse|getPreparedPartResponse)", body))

            if has_fault:
                status = "SOAP_FAULT"
                print(f"     ✗ SOAP FAULT (HTTP {http})")
                fs = re.search(r"<faultstring[^>]*>(.*?)</faultstring>", body, re.DOTALL)
                print(f"       faultstring: {fs.group(1)[:300]}" if fs else "")
            elif has_error_info:
                code = found_code.group(1) if found_code else "?"
                msg = (found_message.group(1).strip()[:300] if found_message else "").replace(": ", "\n         ")
                status = f"EIS_ERROR (code={code})"
                print(f"     ✗ EIS error code={code}")
                print(f"       {msg}")
            elif has_archive:
                status = "SUCCESS (archiveUrl found)"
                print(f"     ✓ SUCCESS — archiveUrl present (HTTP {http})")
                for url in re.findall(r"<archiveUrl[^>]*>(.*?)</archiveUrl>", body):
                    print(f"       archiveUrl: {url}")
            elif has_nsi_data:
                status = "SUCCESS (NSI data received)"
                print(f"     ✓ SUCCESS — NSI data received (HTTP {http})")
            elif has_no_data:
                status = "SUCCESS (noData=true)"
                print(f"     ✓ SUCCESS — server returned noData (HTTP {http})")
            elif is_bus_ack and not is_eis_response:
                status = "BUS_ACK (not EIS response)"
                print(f"     ~ Bus acknowledgment (not EIS response format)")
            elif is_eis_response:
                status = "EIS_RESPONSE (no archiveUrl)"
                print(f"     ~ EIS response received (HTTP {http}), body length: {len(body)}")
            else:
                status = f"RECEIVED (HTTP {http})"
                print(f"     ? Response received (HTTP {http}), body length: {len(body)}")

            # Save response
            safe_body = body.replace(token, "[REDACTED]") if token else body
            with open(f"/tmp/soapui_probe_{name}_response.xml", "w") as f:
                f.write(safe_body)
            print(f"     Response saved: /tmp/soapui_probe_{name}_response.xml")
            results.append({"operation": name, "status": status, "http": http, "error": None})

    # Summary
    print(f"\n{'='*72}")
    print(f"  SUMMARY")
    print(f"{'='*72}")
    for r in results:
        print(f"  {r['operation']:30s}  {r['status']}")
    print(f"{'='*72}")

    # Exit with non-zero if any error
    if any(r["status"] in ("ERROR", "SOAP_FAULT") for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
