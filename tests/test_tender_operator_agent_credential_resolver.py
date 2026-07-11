from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from src.modules.tender_operator_agent_demo.credential_resolver import (
    PLACEHOLDER_VALUES,
    ResolvedCredential,
    resolve_getdocsip_credential,
)


def test_no_credential_returns_not_configured(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", raising=False)
    result = resolve_getdocsip_credential(allow_legacy_fallback=False)
    assert result.configured is False
    assert result.credential_owner == "document_export"
    assert result.source == "none"


def test_no_credential_with_legacy_gate_off_returns_not_configured(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", raising=False)
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "some-legacy-token")
    result = resolve_getdocsip_credential(allow_legacy_fallback=False)
    assert result.configured is False
    assert result.source == "none"


def test_env_var_token_returns_document_export(monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", "test-doc-export-token")
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", raising=False)
    result = resolve_getdocsip_credential()
    assert result.configured is True
    assert result.credential_owner == "document_export"
    assert result.source == "env_var"
    assert result.token == "test-doc-export-token"
    assert result.sha256_fingerprint != ""
    assert result.legacy_fallback_used is False


def test_placeholder_env_var_is_ignored(monkeypatch):
    for placeholder in PLACEHOLDER_VALUES:
        monkeypatch.setenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", placeholder)
        monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", raising=False)
        result = resolve_getdocsip_credential(allow_legacy_fallback=False)
        assert result.configured is False, f"placeholder={placeholder!r} should be ignored"


def test_legacy_fallback(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", raising=False)
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "legacy-token")
    result = resolve_getdocsip_credential(allow_legacy_fallback=True)
    assert result.configured is True
    assert result.credential_owner == "individual"
    assert result.source == "legacy_env_var"
    assert result.token == "legacy-token"
    assert result.legacy_fallback_used is True
    assert len(result.warnings) == 1


def test_legacy_fallback_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", raising=False)
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "legacy-token")
    result = resolve_getdocsip_credential()
    assert result.configured is False
    assert result.source == "none"


def test_legacy_gate_env_var(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", raising=False)
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "legacy-token")
    monkeypatch.setenv("EIS_ALLOW_LEGACY_INDIVIDUAL_TOKEN", "true")
    result = resolve_getdocsip_credential()
    assert result.configured is True
    assert result.source == "legacy_env_var"


def test_document_export_takes_priority_over_legacy(monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", "doc-export-token")
    monkeypatch.setenv("ZAKUPKI_GOV_RU_SOAP_TOKEN", "legacy-token")
    result = resolve_getdocsip_credential(allow_legacy_fallback=True)
    assert result.configured is True
    assert result.credential_owner == "document_export"
    assert result.source == "env_var"
    assert result.token == "doc-export-token"


def test_token_file_returns_credential(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", raising=False)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("file-token-value\n")
        tmp_path = f.name
    try:
        result = resolve_getdocsip_credential(token_file_path=tmp_path)
        assert result.configured is True
        assert result.credential_owner == "document_export"
        assert result.source == "token_file"
        assert result.token == "file-token-value"
    finally:
        os.unlink(tmp_path)


def test_token_file_env_var(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", raising=False)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("env-file-token\n")
        tmp_path = f.name
    try:
        monkeypatch.setenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", tmp_path)
        result = resolve_getdocsip_credential()
        assert result.configured is True
        assert result.source == "token_file"
        assert result.token == "env-file-token"
    finally:
        os.unlink(tmp_path)


def test_missing_token_file_is_skipped(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", raising=False)
    monkeypatch.setenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", "/nonexistent/path/token.txt")
    result = resolve_getdocsip_credential(allow_legacy_fallback=False)
    assert result.configured is False


def test_token_file_not_specified_skips_file_read(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", raising=False)
    result = resolve_getdocsip_credential(allow_legacy_fallback=False)
    assert result.configured is False
    assert result.source == "none"


def test_sha256_fingerprint_is_consistent(monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", "consistent-fingerprint")
    result1 = resolve_getdocsip_credential()
    result2 = resolve_getdocsip_credential()
    assert result1.sha256_fingerprint == result2.sha256_fingerprint


def test_normalized_length(monkeypatch):
    token = "my-test-token"
    monkeypatch.setenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", token)
    result = resolve_getdocsip_credential()
    assert result.normalized_length == len(token)


def test_resolved_credential_frozen():
    c = ResolvedCredential(configured=False, source="none")
    assert c.configured is False
    assert c.source == "none"
    assert c.credential_owner == "document_export"


def test_resolved_credential_token_not_in_repr():
    c = ResolvedCredential(configured=True, token="secret123")
    assert "secret123" not in repr(c)


def test_empty_env_var_is_ignored(monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", "")
    result = resolve_getdocsip_credential(allow_legacy_fallback=False)
    assert result.configured is False


def test_whitespace_only_env_var_is_ignored(monkeypatch):
    monkeypatch.setenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", "   ")
    result = resolve_getdocsip_credential(allow_legacy_fallback=False)
    assert result.configured is False


def test_resolver_returns_warnings_list(monkeypatch):
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", raising=False)
    monkeypatch.delenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN_FILE", raising=False)
    result = resolve_getdocsip_credential(allow_legacy_fallback=False)
    assert isinstance(result.warnings, list)
    assert any("no GetDocsIP" in w for w in result.warnings)


# ── Security: token absent from repr, exception, health ──

def test_token_absent_from_settings_repr():
    from src.modules.tender_operator_agent_demo.settings import ZakupkiSoapSettings
    s = ZakupkiSoapSettings(enabled=True, token="my-secret-token-123")
    assert "my-secret-token-123" not in repr(s)


def test_token_absent_from_settings_with_doc_export_repr():
    from src.modules.tender_operator_agent_demo.settings import ZakupkiSoapSettings
    s = ZakupkiSoapSettings(enabled=True, token="legacy-token", document_export_token="doc-export-token")
    assert "doc-export-token" not in repr(s)
    assert "legacy-token" not in repr(s)


def test_token_absent_from_safe_status():
    from src.modules.tender_operator_agent_demo.settings import ZakupkiSoapSettings
    s = ZakupkiSoapSettings(enabled=True, token="secret-for-status")
    status_str = str(s.safe_status())
    assert "secret-for-status" not in status_str


def test_safe_status_has_no_token():
    from src.modules.tender_operator_agent_demo.settings import ZakupkiSoapSettings
    s = ZakupkiSoapSettings(enabled=True, token="another-secret")
    status_str = str(s.safe_status())
    assert "another-secret" not in status_str
    assert "credential_owner" in status_str


def test_token_absent_from_health(monkeypatch):
    from src.modules.tender_operator_agent_demo.credential_resolver import resolve_getdocsip_credential
    monkeypatch.setenv("ZAKUPKI_GOV_RU_DOCUMENT_EXPORT_TOKEN", "health-secret-token")
    resolved = resolve_getdocsip_credential()
    assert "health-secret-token" not in repr(resolved)
    assert "health-secret-token" not in str(resolved.warnings)
    assert resolved.sha256_fingerprint != ""
    assert resolved.sha256_fingerprint != hashlib.sha256(b"fake").hexdigest()


def test_token_absent_from_exception():
    from src.modules.tender_operator_agent_demo.zakupki_soap_client import _sanitize_error
    msg = _sanitize_error("error with token abc-123", "abc-123")
    assert "[redacted]" in msg
    assert "abc-123" not in msg


def test_token_resolver_called_once_per_settings_lifecycle():
    from src.modules.tender_operator_agent_demo.settings import (
        ZakupkiSoapSettings,
        _ACTIVE_TOKEN_CACHE,
        reload_active_token,
    )
    call_count = 0

    original_resolve = resolve_getdocsip_credential

    def tracking_resolve(**kwargs):
        nonlocal call_count
        call_count += 1
        return original_resolve(**kwargs)

    import src.modules.tender_operator_agent_demo.settings as settings_mod
    settings_mod.resolve_getdocsip_credential = tracking_resolve

    reload_active_token()
    s = ZakupkiSoapSettings(enabled=False)
    # Fields empty → should call resolver once
    _ = s.active_token
    _ = s.active_token
    _ = s.active_token

    settings_mod.resolve_getdocsip_credential = original_resolve

    assert call_count >= 1  # resolver was called (fields empty, two-step fallback)
    assert call_count <= 2  # cached after first access (no legacy + legacy = 2 calls)


def test_reload_active_token_clears_cache():
    from src.modules.tender_operator_agent_demo.settings import (
        ZakupkiSoapSettings,
        _ACTIVE_TOKEN_CACHE,
        reload_active_token,
    )
    s = ZakupkiSoapSettings(enabled=False)
    _ACTIVE_TOKEN_CACHE[id(s)] = "cached-value"
    reload_active_token()
    assert id(s) not in _ACTIVE_TOKEN_CACHE


def test_doc_export_token_field_does_not_call_resolver():
    from src.modules.tender_operator_agent_demo.settings import (
        ZakupkiSoapSettings,
        _ACTIVE_TOKEN_CACHE,
        reload_active_token,
    )
    call_count = 0
    original_resolve = resolve_getdocsip_credential

    def tracking_resolve(**kwargs):
        nonlocal call_count
        call_count += 1
        return original_resolve(**kwargs)

    import src.modules.tender_operator_agent_demo.settings as settings_mod
    settings_mod.resolve_getdocsip_credential = tracking_resolve

    reload_active_token()
    s = ZakupkiSoapSettings(enabled=True, document_export_token="field-token")
    _ = s.active_token
    _ = s.active_token
    _ = s.active_token

    settings_mod.resolve_getdocsip_credential = original_resolve

    assert call_count == 0  # resolver never called when field is set


def test_legacy_token_field_does_not_call_resolver():
    from src.modules.tender_operator_agent_demo.settings import (
        ZakupkiSoapSettings,
        _ACTIVE_TOKEN_CACHE,
        reload_active_token,
    )
    call_count = 0
    original_resolve = resolve_getdocsip_credential

    def tracking_resolve(**kwargs):
        nonlocal call_count
        call_count += 1
        return original_resolve(**kwargs)

    import src.modules.tender_operator_agent_demo.settings as settings_mod
    settings_mod.resolve_getdocsip_credential = tracking_resolve

    reload_active_token()
    s = ZakupkiSoapSettings(enabled=True, token="field-legacy")
    _ = s.active_token
    _ = s.active_token
    _ = s.active_token

    settings_mod.resolve_getdocsip_credential = original_resolve

    assert call_count == 0  # resolver never called when legacy field is set
