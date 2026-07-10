from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "tools" / "eis_windows_gateway"


def test_windows_gateway_templates_do_not_contain_pin_or_secrets():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.rglob("*") if path.is_file())
    forbidden = ["pin=", "PIN=", "PRIVATE KEY", "BEGIN CERTIFICATE", "ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN="]
    for marker in forbidden:
        assert marker not in combined


def test_gateway_templates_bind_only_localhost():
    for path in (ROOT / "windows").glob("cryptopro-stunnel-*.conf.template"):
        text = path.read_text(encoding="utf-8")
        assert "accept = 127.0.0.1:" in text
        assert "accept = 0.0.0.0:" not in text


def test_mac_forward_targets_windows_localhost_not_eis_directly():
    text = (ROOT / "mac" / "start-ssh-forward.sh").read_text(encoding="utf-8")
    assert "127.0.0.1:${remote_port}" in text
    assert "int44.zakupki.gov.ru:443" not in text
