from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.modules.tender_operator_agent_demo.settings import ZakupkiSoapSettings
from src.modules.tender_operator_agent_demo.zakupki_soap_client import ZakupkiSoapClient


def diagnostics_dir() -> Path:
    return Path("company_agent_runs/zakupki_soap_diagnostics")


def run_diagnostics(
    *,
    settings: ZakupkiSoapSettings,
    reestr_number: str,
    owner: str = "individual",
    method: str = "getDocsByReestrNumber",
    check_xsd: bool = False,
    download_archive: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "token_owner": owner,
        "token_present": settings.token_configured,
        "endpoint": settings.individual_base_url,
        "xsd_url": settings.individual_xsd_url,
        "method": method,
        "reestr_number": reestr_number,
        "xsd_status": "not_checked",
        "soap_post_status": "not_called",
        "response_kind": "not_called",
        "archive_url_present": False,
        "download_status": "not_requested",
        "sanitized_error": "",
    }
    if not settings.configured:
        payload["soap_post_status"] = "not_configured"
        return payload

    client = ZakupkiSoapClient(settings)
    if check_xsd:
        xsd_probe = client.probe_xsd()
        payload["xsd_status"] = xsd_probe.get("status", "unknown")
        if xsd_probe.get("status") == "error":
            payload["sanitized_error"] = str(xsd_probe.get("error", ""))

    try:
        result = client.get_docs_by_reestr_number(reestr_number)
    except RuntimeError as exc:
        payload["soap_post_status"] = "transport_error"
        payload["response_kind"] = "transport_error"
        payload["sanitized_error"] = str(exc)
        return payload

    payload["soap_post_status"] = "ok"
    payload["response_kind"] = result.status
    payload["archive_url_present"] = bool(result.archive_url)
    payload["ref_id_present"] = bool(result.ref_id)
    if result.warnings and not payload["sanitized_error"]:
        payload["sanitized_error"] = " ".join(result.warnings)

    if download_archive and result.archive_url:
        try:
            target_dir = diagnostics_dir() / "downloads"
            downloaded = client.download_archive(result.archive_url, target_dir)
            payload["download_status"] = "downloaded"
            payload["downloaded_size_bytes"] = downloaded.size_bytes
            payload["archive_url_summary"] = {
                "host": downloaded.source_url_host,
                "path": downloaded.source_url_path,
            }
        except RuntimeError as exc:
            payload["download_status"] = "download_error"
            payload["sanitized_error"] = str(exc)
    elif result.archive_url:
        parsed = result.safe_diagnostic
        payload["archive_url_summary"] = {
            "host": result.archive_url.split("/")[2] if "://" in result.archive_url else "",
            "path": "/" + "/".join(result.archive_url.split("/")[3:]) if "://" in result.archive_url else "",
        }
    else:
        payload["download_status"] = "no_archive_url"

    return payload


def save_diagnostics(payload: dict[str, Any]) -> Path:
    target_dir = diagnostics_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "last_cli_diagnostics.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only диагностика getDocsIP для токена физлица")
    parser.add_argument("--owner", default="individual")
    parser.add_argument("--method", default="getDocsByReestrNumber")
    parser.add_argument("--reestr-number", required=True)
    parser.add_argument("--check-xsd", action="store_true")
    parser.add_argument("--download-archive", action="store_true")
    parser.add_argument("--no-download", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = ZakupkiSoapSettings.from_env()
    payload = run_diagnostics(
        settings=settings,
        reestr_number=args.reestr_number,
        owner=args.owner,
        method=args.method,
        check_xsd=args.check_xsd,
        download_archive=args.download_archive and not args.no_download,
    )
    save_diagnostics(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
