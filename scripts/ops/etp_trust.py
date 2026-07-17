#!/usr/bin/env python3
"""Owner-controlled, fail-closed trust policy for ETP hosts."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import ssl
import subprocess
import sys
import socket
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.shared.network.etp_trust import (  # noqa: E402
    ETPTrustConfigurationError,
    build_ssl_context,
    load_trust_policy,
    should_bypass_proxy,
)


ROOT = Path(os.environ.get("ARVECTUM_ETP_TRUST_DIR", "/Users/master/.config/arvectum/trust"))
POLICY = ROOT / "policy.yaml"


def _inspect(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise ETPTrustConfigurationError("Certificate file must be a regular file")
    raw = path.read_bytes()
    try:
        info = ssl._ssl._test_decode_cert(str(path))
        der = subprocess.run(["openssl", "x509", "-in", str(path), "-outform", "DER"], check=True, capture_output=True).stdout
        text = subprocess.run(["openssl", "x509", "-in", str(path), "-noout", "-text"], check=True, capture_output=True, text=True).stdout
    except ssl.SSLError:
        der = subprocess.run(["openssl", "x509", "-inform", "DER", "-in", str(path), "-outform", "DER"], check=True, capture_output=True).stdout
        pem = subprocess.run(["openssl", "x509", "-inform", "DER", "-in", str(path), "-outform", "PEM"], check=True, capture_output=True).stdout
        with tempfile.NamedTemporaryFile(suffix=".pem") as converted:
            converted.write(pem)
            converted.flush()
            info = ssl._ssl._test_decode_cert(converted.name)
        text = subprocess.run(["openssl", "x509", "-inform", "DER", "-in", str(path), "-noout", "-text"], check=True, capture_output=True, text=True).stdout
    return {
        "subject": str(info.get("subject", "")),
        "issuer": str(info.get("issuer", "")),
        "serial": str(info.get("serialNumber", "")),
        "not_before": str(info.get("notBefore", "")),
        "not_after": str(info.get("notAfter", "")),
        "ca": "CA:TRUE" if "CA:TRUE" in text else "CA:FALSE",
        "certificate_sha256": hashlib.sha256(der).hexdigest().upper(),
        "file_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def _write_policy(data: dict) -> None:
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(ROOT, 0o700)
    POLICY.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    os.chmod(POLICY, 0o600)


def cmd_inspect(args: argparse.Namespace) -> None:
    for key, value in _inspect(Path(args.file)).items():
        print(f"{key}: {value}")


def cmd_add_authority(args: argparse.Namespace) -> None:
    source = Path(args.file).resolve()
    meta = _inspect(source)
    if meta["certificate_sha256"] != args.expected_sha256.replace(":", "").upper():
        raise SystemExit("fingerprint mismatch; authority was not added")
    if meta["ca"] != "CA:TRUE":
        raise SystemExit("certificate is not a CA; authority was not added")
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    (ROOT / "certs").mkdir(mode=0o700, exist_ok=True)
    destination = ROOT / "certs" / f"{args.name}.pem"
    shutil.copyfile(source, destination)
    os.chmod(destination, 0o600)
    data = yaml.safe_load(POLICY.read_text(encoding="utf-8")) if POLICY.exists() else {
        "version": 1,
        "enabled": True,
        "proxy_bypass_enabled": True,
        "defaults": {"verify_hostname": True, "verify_certificate": True, "fail_closed": True},
        "authorities": {},
        "hosts": {},
    }
    backup = ROOT / "backups" / f"policy-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.yaml"
    if POLICY.exists():
        backup.parent.mkdir(mode=0o700, exist_ok=True)
        shutil.copyfile(POLICY, backup)
        os.chmod(backup, 0o600)
    data.setdefault("authorities", {})[args.name] = {"file": f"certs/{destination.name}", "certificate_sha256": meta["certificate_sha256"]}
    _write_policy(data)
    print(f"authority_added: {args.name}")


def _load() -> dict:
    if not POLICY.exists():
        return {"version": 1, "enabled": False, "authorities": {}, "hosts": {}}
    return yaml.safe_load(POLICY.read_text(encoding="utf-8")) or {}


def cmd_add_host(args: argparse.Namespace) -> None:
    if args.host == "*" or "*" in args.host or not (args.host.startswith(".") or "." in args.host):
        raise SystemExit("host must be an exact hostname or explicit dot-prefixed suffix")
    data = _load()
    data.setdefault("hosts", {})[args.host.lower()] = {"authority": args.authority, "direct_connection": bool(args.direct)}
    data["enabled"] = True
    _write_policy(data)
    print(f"host_added: {args.host.lower()}")


def cmd_list(_args: argparse.Namespace) -> None:
    data = _load()
    for name in (data.get("authorities") or {}):
        print(f"authority: {name}")
    for host, rule in (data.get("hosts") or {}).items():
        print(f"host: {host} authority={rule.get('authority')} direct={rule.get('direct_connection', False)}")


def cmd_verify_host(args: argparse.Namespace) -> None:
    policy = load_trust_policy(POLICY)
    context = build_ssl_context(args.host, policy)
    with socket.create_connection((args.host, args.port), timeout=args.timeout) as raw:
        with context.wrap_socket(raw, server_hostname=args.host) as tls:
            peer = tls.getpeercert()
            print("ETP_TLS_TRUST_OK")
            print(f"hostname: {args.host}")
            print(f"port: {args.port}")
            print(f"tls_version: {tls.version()}")
            print(f"subject: {peer.get('subject', '')}")
            print(f"issuer: {peer.get('issuer', '')}")
            print(f"proxy_bypassed: {should_bypass_proxy(args.host, policy)}")


def cmd_remove_host(args: argparse.Namespace) -> None:
    data = _load()
    hosts = data.get("hosts") or {}
    if args.host not in hosts:
        raise SystemExit(f"host is not configured: {args.host}")
    backup = ROOT / "backups" / f"policy-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.yaml"
    backup.parent.mkdir(mode=0o700, exist_ok=True)
    if POLICY.exists():
        shutil.copyfile(POLICY, backup)
        os.chmod(backup, 0o600)
    del hosts[args.host]
    data["hosts"] = hosts
    _write_policy(data)
    print(f"host_removed: {args.host}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("inspect-cert")
    p.add_argument("--file", required=True)
    p.set_defaults(func=cmd_inspect)
    p = subs.add_parser("add-authority")
    p.add_argument("--name", required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--expected-sha256", required=True)
    p.set_defaults(func=cmd_add_authority)
    p = subs.add_parser("add-host")
    p.add_argument("--host", required=True)
    p.add_argument("--authority", required=True)
    p.add_argument("--direct", action="store_true")
    p.set_defaults(func=cmd_add_host)
    p = subs.add_parser("list")
    p.set_defaults(func=cmd_list)
    p = subs.add_parser("verify-host")
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, default=443)
    p.add_argument("--timeout", type=float, default=10.0)
    p.set_defaults(func=cmd_verify_host)
    p = subs.add_parser("remove-host")
    p.add_argument("--host", required=True)
    p.set_defaults(func=cmd_remove_host)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
