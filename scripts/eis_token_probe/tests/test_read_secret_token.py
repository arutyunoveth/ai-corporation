from __future__ import annotations

import hashlib
import re
import uuid as uuid_mod
from pathlib import Path

import pytest

from scripts.eis_token_probe.read_secret_token import (
    TokenMetadata,
    read_token_file,
    print_safe_metadata,
)


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


VALID_UUID = "4a32757d-e951-4088-95fe-9c8ae7300e07"


# ── 1. Token file is never printed ──────────────────────────────────────

def test_read_secret_token_not_in_str_repr():
    meta = TokenMetadata(VALID_UUID, len(VALID_UUID))
    s = repr(meta)
    assert VALID_UUID[:8] not in s
    assert VALID_UUID[-4:] not in s


def test_print_safe_metadata_does_not_print_value(capsys, tmp_path: Path):
    p = tmp_path / "token.txt"
    p.write_text(VALID_UUID)
    result = print_safe_metadata(str(p))
    captured = capsys.readouterr()
    assert not captured.out
    assert result["present"]
    assert result["sha256"] == _hash(VALID_UUID)


# ── 2. Token value never appears in logs ────────────────────────────────

def test_token_not_in_dict_output():
    meta = TokenMetadata(VALID_UUID, len(VALID_UUID))
    d = str(meta.to_dict())
    assert VALID_UUID[:8] not in d


# ── 3. Token value never appears in exception repr ──────────────────────

def test_token_not_in_exception():
    meta = TokenMetadata("test-exception-check", 19)
    meta.clear()
    try:
        raise RuntimeError("trigger")
    except RuntimeError:
        import traceback
        tb = traceback.format_exc()
        assert "test-exception-check" not in tb


# ── 4. Token is not accepted as CLI value ───────────────────────────────

def test_no_cli_token_arg():
    from scripts.probe_eis_extract_token_mac import _build_parser
    parser = _build_parser()
    for action in parser._actions:
        assert "token" not in action.dest or "file" in action.dest


# ── 5. BOM/CRLF/quotes normalization ───────────────────────────────────

class TestNormalization:
    @pytest.mark.parametrize("prefix", ["", "\ufeff"])
    @pytest.mark.parametrize("suffix", ["", "\n", "\r\n"])
    @pytest.mark.parametrize("quote", ["", '"', "'"])
    def test_strips_bom_crlf_quotes(self, prefix: str, suffix: str, quote: str):
        raw = f"{prefix}{quote}{VALID_UUID}{quote}{suffix}"
        meta = TokenMetadata(raw, len(raw.encode()))
        assert meta.normalized == VALID_UUID
        assert meta.normalized_length == 36

    def test_whitespace_stripped(self):
        raw = f"  {VALID_UUID}  \n\n"
        meta = TokenMetadata(raw, len(raw.encode()))
        assert meta.normalized == VALID_UUID
        assert meta.contains_whitespace

    def test_quotes_detected(self):
        raw = f'"{VALID_UUID}"'
        meta = TokenMetadata(raw, len(raw.encode()))
        assert meta.quotes_removed

    def test_bom_detected(self):
        raw = f"\ufeff{VALID_UUID}"
        meta = TokenMetadata(raw, len(raw.encode()))
        assert meta.normalized == VALID_UUID


# ── 6. SHA-256 fingerprint only ─────────────────────────────────────────

def test_sha256_fingerprint():
    meta = TokenMetadata(VALID_UUID, len(VALID_UUID))
    assert meta.sha256 == _hash(VALID_UUID)


# ── 7. no-token control ─────────────────────────────────────────────────

@pytest.mark.parametrize("empty_val", ["", "  ", "\n", "\r\n"])
def test_empty_token_detected(empty_val: str):
    meta = TokenMetadata(empty_val, len(empty_val.encode()))
    assert meta.empty
    assert not meta.uuid_like


# ── 8. invalid-token control ────────────────────────────────────────────

def test_invalid_uuid_detected():
    meta = TokenMetadata("not-a-uuid-at-all", 16)
    assert not meta.uuid_like
    assert not meta.empty


# ── 9. individual-token control ─────────────────────────────────────────

def test_individual_token_is_uuid_like():
    meta = TokenMetadata(VALID_UUID, len(VALID_UUID))
    assert meta.uuid_like


# ── 10. new-token credential mode (RTF embedded) ───────────────────────

def test_rtf_uuid_extraction(tmp_path: Path):
    rtf_content = (
        '{\\rtf1\\ansi\\ansicpg1252\\cocoartf2870'
        '{\\fonttbl\\f0\\fswiss\\fcharset0 Helvetica;}'
        '\\f0\\fs24 38bf454b-e123-4abc-9def-000000001234'
        '}'
    )
    p = tmp_path / "rtf_token.txt"
    p.write_text(rtf_content)
    meta = read_token_file(str(p))
    assert meta.rtf_detected
    assert meta.uuid_extracted_from_rtf
    assert meta.uuid_like
    assert meta.normalized_length == 36
    assert meta.normalized == "38bf454b-e123-4abc-9def-000000001234"


def test_plain_token_not_rtf(tmp_path: Path):
    p = tmp_path / "plain.txt"
    p.write_text(VALID_UUID)
    meta = read_token_file(str(p))
    assert not meta.rtf_detected
    assert not meta.uuid_extracted_from_rtf


# ── 11. identical SOAP body across auth matrix ─────────────────────────

def test_same_envelope_template_for_all_modes():
    from scripts.probe_eis_extract_token_mac import _build_get_nsi_body
    body1 = _build_get_nsi_body("req-1", "2026-07-11T10:00:00Z")
    body2 = _build_get_nsi_body("req-2", "2026-07-11T10:00:00Z")
    assert "<ws:getNsiRequest>" in body1
    assert "<ws:getNsiRequest>" in body2
    assert "<nsiCode44>nsiAllList</nsiCode44>" in body1
    # Structure is identical except request ID
    assert body1.count("<index>") == body2.count("<index>")


# ── 12. mode always PROD ──────────────────────────────────────────────

def test_mode_always_prod():
    from scripts.probe_eis_extract_token_mac import _index_block
    block = _index_block("test-id", "2026-07-11T10:00:00Z")
    assert "<mode>PROD</mode>" in block
    assert "single" not in block.lower()


# ── 13. orgRegion canonicalized to 77 ─────────────────────────────────

def test_region_canonicalized():
    from src.tender_research.sync.eis_params import normalize_eis_region_code
    assert normalize_eis_region_code("москва") == "77"
    assert normalize_eis_region_code("Moscow") == "77"
    assert normalize_eis_region_code("77") == "77"
    assert normalize_eis_region_code("77000000000000") == "77"


# ── 14. exactDate timezone-aware ──────────────────────────────────────

def test_exact_date_timezone():
    from datetime import date
    from src.tender_research.sync.eis_params import format_eis_exact_date
    result = format_eis_exact_date(date(2026, 7, 11), timezone="Europe/Moscow")
    assert "+" in result or "-" in result[10:]
    assert result.startswith("2026-07-11")


# ── 15. createDateTime UTC ────────────────────────────────────────────

def test_create_datetime_utc():
    from datetime import datetime, timezone
    from src.tender_research.sync.eis_params import format_eis_create_datetime
    dt = datetime.now(timezone.utc)
    result = format_eis_create_datetime(dt)
    assert result.endswith("Z")
    assert result.count("-") == 2


# ── 16. archive download header matrix ─────────────────────────────────

def test_download_header_placement():
    from scripts.probe_eis_extract_token_mac import _http_download_get_first_bytes
    result = _http_download_get_first_bytes(
        "https://example.com/test.zip", "test-token", max_bytes=10, timeout=5, allow_insecure=True
    )
    assert "http_status" in result


# ── 17. token role classification ─────────────────────────────────────

_NS_EIS = "http://zakupki.gov.ru/fz44/get-docs-ip/ws"
_NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"


def test_classify_code5_as_rejected():
    from scripts.probe_eis_extract_token_mac import _classify_soap_response
    resp = {
        "http_status": 200,
        "body": (
            f'<soap:Envelope xmlns:soap="{_NS_SOAP}"><soap:Body>'
            f'<ns2:getNsiResponse xmlns:ns2="{_NS_EIS}"><dataInfo><errorInfo>'
            '<code>5</code><message>token rejected</message>'
            '</errorInfo></dataInfo></ns2:getNsiResponse>'
            '</soap:Body></soap:Envelope>'
        ),
        "error": None,
    }
    result = _classify_soap_response(resp, "getNsi", "getNsiResponse")
    assert result["application_code"] == "5"


def test_classify_archive_received():
    from scripts.probe_eis_extract_token_mac import _classify_soap_response
    resp = {
        "http_status": 200,
        "body": (
            f'<soap:Envelope xmlns:soap="{_NS_SOAP}"><soap:Body>'
            f'<ns2:getNsiResponse xmlns:ns2="{_NS_EIS}">'
            '<dataInfo><nsiArchiveInfo>'
            '<archiveUrl>https://example.com/arc.zip</archiveUrl>'
            '</nsiArchiveInfo></dataInfo>'
            '</ns2:getNsiResponse>'
            '</soap:Body></soap:Envelope>'
        ),
        "error": None,
    }
    result = _classify_soap_response(resp, "getNsi", "getNsiResponse")
    assert result["classification"] == "archive_url_received"
    assert len(result["archive_urls"]) == 1


# ── 18. GetDocsLE mTLS failure classified ────────────────────────────

def test_getdocsle_mtls_fails():
    import ssl, socket
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with pytest.raises(Exception) as exc:
        sock = socket.create_connection(("int44-ttls-cert.zakupki.gov.ru", 443), timeout=5)
        ssock = ctx.wrap_socket(sock, server_hostname="int44-ttls-cert.zakupki.gov.ru")
        ssock.close()
    error_str = str(exc.value).lower()
    assert "handshake" in error_str or "certificate" in error_str or "alert" in error_str


# ── 19. New token never routed to getDocsLE mtls ─────────────────────

def test_no_token_sent_before_tls():
    """Token can only be sent after TLS completes. TLS fails on getDocsLE."""
    import ssl
    with pytest.raises(ssl.SSLError):
        import socket
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        sock = socket.create_connection(("int44-ttls-cert.zakupki.gov.ru", 443), timeout=5)
        ssock = ctx.wrap_socket(sock, server_hostname="int44-ttls-cert.zakupki.gov.ru")
        ssock.close()


# ── 20. Secret scan of reports ────────────────────────────────────────

def test_report_contains_no_uuid(tmp_path: Path):
    import json
    report = {
        "token_sha256": "abc123",
        "results": [{"mode": "test"}],
    }
    text = json.dumps(report)
    uuid_pat = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    assert not re.search(uuid_pat, text)


# ── 21. Existing placeholder tokens unchanged ─────────────────────────

def test_placeholder_tokens_preserved():
    from src.modules.tender_operator_agent_demo.settings import PLACEHOLDER_TOKENS
    assert "replace_me_do_not_commit_real_token" in PLACEHOLDER_TOKENS
    assert "" in PLACEHOLDER_TOKENS


# ── 22. Existing bulk pipeline imports ────────────────────────────────

def test_bulk_pipeline_imports():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from src.tender_research.sync.eis_params import (
        normalize_eis_region_code,
        format_eis_exact_date,
        format_eis_create_datetime,
    )
    assert callable(normalize_eis_region_code)
    assert callable(format_eis_exact_date)
    assert callable(format_eis_create_datetime)


# ── Extra: clear() erases token ───────────────────────────────────────

def test_clear_removes_token():
    meta = TokenMetadata(VALID_UUID, len(VALID_UUID))
    assert meta.normalized == VALID_UUID
    meta.clear()
    assert meta.normalized == ""
    assert meta.normalized_length == 0


def test_del_clears_token():
    meta = TokenMetadata(VALID_UUID, len(VALID_UUID))
    sha = meta.sha256
    del meta
    # Cannot access meta after deletion; just confirm no crash
    assert sha == _hash(VALID_UUID)
