from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from src.shared.network.etp_trust import (
    Authority,
    ETPTrustConfigurationError,
    HostPolicy,
    TrustPolicy,
    build_ssl_context,
    resolve_host_policy,
    should_bypass_proxy,
    validate_ca_file,
)


def _ca(tmp_path: Path) -> Path:
    key = tmp_path / "ca.key"
    cert = tmp_path / "ca.pem"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", str(key), "-out", str(cert), "-days", "2", "-nodes", "-subj", "/CN=Test CA", "-addext", "basicConstraints=critical,CA:TRUE"],
        check=True,
        capture_output=True,
    )
    return cert


def _policy(cert: Path, enabled: bool = True) -> TrustPolicy:
    return TrustPolicy(
        enabled=enabled,
        authorities={"test": Authority("test", cert, _der_sha(cert))},
        hosts=(HostPolicy(".zakupki.gov.ru", "test", True), HostPolicy("zakupki.gov.ru", "test", True)),
    )


def _der_sha(cert: Path) -> str:
    command = ["openssl", "x509", "-in", str(cert), "-outform", "DER"]
    if cert.suffix == ".der":
        command[2:2] = ["-inform", "DER"]
    der = subprocess.run(command, check=True, capture_output=True).stdout
    return hashlib.sha256(der).hexdigest().upper()


def test_suffix_matching_is_boundary_safe(tmp_path: Path):
    policy = _policy(_ca(tmp_path))
    assert resolve_host_policy("api.zakupki.gov.ru", policy)
    assert resolve_host_policy("evil-zakupki.gov.ru.example.com", policy) is None


def test_unknown_host_keeps_strict_default_and_no_proxy_bypass(tmp_path: Path):
    policy = _policy(_ca(tmp_path))
    context = build_ssl_context("example.com", policy)
    assert context.verify_mode.value == 2
    assert context.check_hostname is True
    assert should_bypass_proxy("example.com", policy) is False


def test_allowed_host_gets_extra_ca_and_direct_policy(tmp_path: Path):
    cert = _ca(tmp_path)
    context = build_ssl_context("zakupki.gov.ru", _policy(cert))
    assert context.verify_mode.value == 2
    assert context.check_hostname is True
    assert should_bypass_proxy("api.zakupki.gov.ru", _policy(cert)) is True


def test_system_authority_is_strict_and_allowlisted(tmp_path: Path):
    policy = TrustPolicy(
        enabled=True,
        authorities={"macos_system": Authority("macos_system", type="system")},
        hosts=(HostPolicy("zakupki.gov.ru", "macos_system", True),),
    )
    context = build_ssl_context("zakupki.gov.ru", policy)
    assert context.verify_mode.value == 2
    assert context.check_hostname is True
    assert should_bypass_proxy("zakupki.gov.ru", policy) is True
    assert should_bypass_proxy("example.com", policy) is False


def test_fingerprint_mismatch_and_missing_file_fail_closed(tmp_path: Path):
    cert = _ca(tmp_path)
    with pytest.raises(ETPTrustConfigurationError):
        validate_ca_file(Authority("test", cert, "0" * 64))
    with pytest.raises(ETPTrustConfigurationError):
        validate_ca_file(Authority("test", tmp_path / "missing.pem", "0" * 64))


def test_pem_and_der_share_certificate_fingerprint_but_not_file_hash(tmp_path: Path):
    pem = _ca(tmp_path)
    der = tmp_path / "ca.der"
    der.write_bytes(subprocess.run(["openssl", "x509", "-in", str(pem), "-outform", "DER"], check=True, capture_output=True).stdout)
    assert _der_sha(pem) == _der_sha(der)
    assert hashlib.sha256(pem.read_bytes()).hexdigest() != hashlib.sha256(der.read_bytes()).hexdigest()
    authority = Authority("test", der, _der_sha(pem))
    assert validate_ca_file(authority) == der
