from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any


PLACEHOLDER_TOKENS = {
    "",
    "replace_me",
    "replace_me_do_not_commit_real_token",
    "insert_token_here",
    "вставить_токен_сюда",
}


def _read_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_int(name: str, default: int, *, minimum: int = 1) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return max(int(value), minimum)
    except ValueError:
        return default


@dataclass(frozen=True)
class ZakupkiSoapSettings:
    enabled: bool = False
    token: str = field(default="", repr=False)
    base_url: str = "https://int44.zakupki.gov.ru/eis-integration/services-vbs"
    search_action: str = "searchProcurements"
    details_action: str = "getProcurementDetails"
    attachments_action: str = "listAttachments"
    timeout_seconds: int = 30
    max_results: int = 10
    max_attachments: int = 20
    max_download_mb: int = 200
    trust_env_proxy: bool = False
    debug: bool = False

    @classmethod
    def from_env(cls) -> "ZakupkiSoapSettings":
        return cls(
            enabled=_read_bool("ZAKUPKI_GOV_RU_SOAP_ENABLED", False),
            token=os.environ.get("ZAKUPKI_GOV_RU_SOAP_TOKEN", "").strip(),
            base_url=os.environ.get(
                "ZAKUPKI_GOV_RU_SOAP_BASE_URL",
                "https://int44.zakupki.gov.ru/eis-integration/services-vbs",
            ).strip()
            or "https://int44.zakupki.gov.ru/eis-integration/services-vbs",
            search_action=os.environ.get("ZAKUPKI_GOV_RU_SOAP_SEARCH_ACTION", "searchProcurements").strip()
            or "searchProcurements",
            details_action=os.environ.get("ZAKUPKI_GOV_RU_SOAP_DETAILS_ACTION", "getProcurementDetails").strip()
            or "getProcurementDetails",
            attachments_action=os.environ.get("ZAKUPKI_GOV_RU_SOAP_ATTACHMENTS_ACTION", "listAttachments").strip()
            or "listAttachments",
            timeout_seconds=_read_int("ZAKUPKI_GOV_RU_SOAP_TIMEOUT_SECONDS", 30),
            max_results=_read_int("ZAKUPKI_GOV_RU_SOAP_MAX_RESULTS", 10),
            max_attachments=_read_int("ZAKUPKI_GOV_RU_SOAP_MAX_ATTACHMENTS", 20),
            max_download_mb=_read_int("ZAKUPKI_GOV_RU_SOAP_MAX_DOWNLOAD_MB", 200),
            trust_env_proxy=_read_bool("ZAKUPKI_GOV_RU_SOAP_TRUST_ENV_PROXY", False),
            debug=_read_bool("ZAKUPKI_GOV_RU_SOAP_DEBUG", False),
        )

    @property
    def token_configured(self) -> bool:
        return self.token.strip().lower() not in PLACEHOLDER_TOKENS

    @property
    def configured(self) -> bool:
        return self.enabled and self.token_configured

    def safe_status(self) -> dict[str, Any]:
        reason = None
        if not self.token_configured:
            reason = "Источник ЕИС не настроен: добавьте ZAKUPKI_GOV_RU_SOAP_TOKEN в .env.local"
        elif not self.enabled:
            reason = "Источник ЕИС не включён: установите ZAKUPKI_GOV_RU_SOAP_ENABLED=1"
        return {
            "source": "zakupki_gov_ru_soap",
            "enabled": self.enabled,
            "configured": self.configured,
            "reason": reason,
            "base_url_configured": bool(self.base_url),
            "search_action": self.search_action,
            "details_action": self.details_action,
            "attachments_action": self.attachments_action,
            "timeout_seconds": self.timeout_seconds,
            "max_results": self.max_results,
            "max_attachments": self.max_attachments,
            "max_download_mb": self.max_download_mb,
            "trust_env_proxy": self.trust_env_proxy,
            "debug": self.debug,
        }


def is_zakupki_soap_configured(settings: ZakupkiSoapSettings | None = None) -> bool:
    return (settings or get_zakupki_soap_settings()).configured


@lru_cache(maxsize=1)
def get_zakupki_soap_settings() -> ZakupkiSoapSettings:
    return ZakupkiSoapSettings.from_env()


def clear_zakupki_soap_settings_cache() -> None:
    get_zakupki_soap_settings.cache_clear()
