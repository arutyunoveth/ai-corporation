from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.diagnose_eis_soap_matrix import (
    ProbeResult,
    build_docs_envelope,
    build_search_envelope,
    classify_transport_error,
    conclude,
    fingerprint,
    results_to_json,
)


def test_fingerprint_masks_middle():
    assert fingerprint("0123456789abcdef") == "0123...cdef"


def test_fingerprint_short_token():
    assert fingerprint("abc") == "abc"


def test_fingerprint_empty():
    assert fingerprint("") == "none"


def test_tls_reset_classified_as_transport_failure():
    err = URLError("Connection reset by peer")
    ts, msg = classify_transport_error(err)
    assert ts == "tls_reset"


def test_handshake_failure_classified():
    err = URLError("ssl/tls alert handshake failure")
    ts, msg = classify_transport_error(err)
    assert ts == "handshake_failure"


def test_timeout_classified():
    err = URLError("timed out")
    ts, msg = classify_transport_error(err)
    assert ts == "timeout"


def test_dns_error_classified():
    err = URLError("Name or service not known")
    ts, msg = classify_transport_error(err)
    assert ts == "dns_error"


def test_tcp_refused_classified():
    err = URLError("Connection refused")
    ts, msg = classify_transport_error(err)
    assert ts == "tcp_error"


def test_http_403_classified_as_auth_failure():
    r = ProbeResult(
        transport_status="tls_ok",
        http_status=403,
        soap_status="invalid_request",
    )
    c = conclude(r)
    assert c == "token_rejected"


def test_http_401_classified_as_auth_failure():
    r = ProbeResult(
        transport_status="tls_ok",
        http_status=401,
        soap_status="invalid_request",
    )
    c = conclude(r)
    assert c == "token_rejected"


def test_soap_ok_classified_usable():
    r = ProbeResult(transport_status="tls_ok", soap_status="soap_ok", http_status=200)
    assert conclude(r) == "usable_without_rutoken"


def test_wsdl_ok_classified_usable():
    r = ProbeResult(transport_status="tls_ok", soap_status="wsdl_loaded", http_status=200)
    assert conclude(r) == "usable_without_rutoken"


def test_soap_fault_classified_token_rejected():
    r = ProbeResult(transport_status="tls_ok", soap_status="soap_fault", http_status=200)
    assert conclude(r) == "token_rejected"


def test_tls_reset_conclusion():
    r = ProbeResult(transport_status="tls_reset")
    assert conclude(r) == "requires_gost_gateway"


def test_handshake_failure_conclusion():
    r = ProbeResult(transport_status="handshake_failure")
    assert conclude(r) == "requires_gost_gateway"


def test_dns_error_conclusion():
    r = ProbeResult(transport_status="dns_error")
    assert conclude(r) == "endpoint_unavailable"


def test_tcp_error_conclusion():
    r = ProbeResult(transport_status="tcp_error")
    assert conclude(r) == "endpoint_unavailable"


def test_unknown_transport_conclusion():
    r = ProbeResult(transport_status="unknown")
    assert conclude(r) == "endpoint_unavailable"


def test_report_contains_conclusion():
    results = [
        ProbeResult(capability="docs", endpoint_name="test", transport_status="tls_ok",
                     soap_status="soap_ok", conclusion="usable_without_rutoken"),
        ProbeResult(capability="search", endpoint_name="test2", transport_status="tls_reset",
                     soap_status="not_checked", conclusion="requires_gost_gateway"),
    ]
    report = results_to_json(results)
    assert "usable_without_rutoken" in str(report)
    assert "requires_gost_gateway" in str(report)
    assert report["summary"]["total"] == 2
    assert report["summary"]["usable_without_rutoken"] == 1
    assert report["summary"]["requires_gost_gateway"] == 1


def test_docs_envelope_contains_token():
    token = "test-token-1234"
    env = build_docs_envelope(token, "0373100000124000001")
    assert token in env
    assert "getDocsByReestrNumberRequest" in env
    assert "individualPerson_token" in env


def test_search_envelope_contains_legal_token():
    token = "legal-token-5678"
    env = build_search_envelope(token, "кабель", 3)
    assert token in env
    assert "searchProcurements" in env
    assert "usertoken" in env


def test_matrix_does_not_log_full_tokens():
    from scripts.diagnose_eis_soap_matrix import _sanitize
    os.environ["ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN"] = "4a32757d-e951-4088-95fe-9c8ae7300e07"
    msg = "some error with token 4a32757d-e951-4088-95fe-9c8ae7300e07 inside"
    sanitized = _sanitize(msg)
    assert "4a32757d-e951-4088-95fe-9c8ae7300e07" not in sanitized
    assert "[redacted]" in sanitized
    del os.environ["ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN"]


def test_http_error_403_raw():
    r = ProbeResult(transport_status="http_error", http_status=403, error_class="HTTPError")
    assert conclude(r) == "endpoint_unavailable"


def test_sanitize_multiple_tokens():
    os.environ["ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN"] = "token-a"
    os.environ["ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN"] = "token-b"
    from scripts.diagnose_eis_soap_matrix import _sanitize
    msg = "error: token-a and token-b seen"
    sanitized = _sanitize(msg)
    assert "token-a" not in sanitized
    assert "token-b" not in sanitized
    assert "[redacted]" in sanitized
    del os.environ["ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN"]
    del os.environ["ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN"]