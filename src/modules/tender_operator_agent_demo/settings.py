from __future__ import annotations

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal


PLACEHOLDER_TOKENS = {
    "",
    "replace_me",
    "replace_me_do_not_commit_real_token",
    "insert_token_here",
    "вставить_токен_сюда",
}

DEFAULT_LEGACY_BASE_URL = "https://int44.zakupki.gov.ru/eis-integration/services-vbs"
DEFAULT_INDIVIDUAL_BASE_URL = "https://int.zakupki.gov.ru/eis-integration/services/getDocsIP"
DEFAULT_INDIVIDUAL_XSD_URL = f"{DEFAULT_INDIVIDUAL_BASE_URL}?xsd=getDocsIP-ws-api.xsd"
DEFAULT_INDIVIDUAL_NAMESPACE = "http://zakupki.gov.ru/fz44/get-docs-ip/ws"
DEFAULT_TOKEN_HEADER_NAME = "individualPerson_token"
DEFAULT_SOAP_MODE = "PROD"
DEFAULT_ALLOWED_HOSTS = "zakupki.gov.ru,.zakupki.gov.ru,int.zakupki.gov.ru,int44.zakupki.gov.ru,int44-ttls-cert.zakupki.gov.ru"
DEFAULT_USER_AGENT = "ArvectumTenderAgent/0.1 read-only"
DEFAULT_CONTENT_TYPE = "text/xml; charset=utf-8"
DEFAULT_SOAP_ACTION_URI = "http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip"
_ENV_FILES_SEEDED = False

TokenOwner = Literal["individual", "legal_entity"]
SoapTransportMode = Literal["direct", "gateway", "disabled"]


def _settings_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _seed_env_from_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def _seed_env_from_local_files() -> None:
    global _ENV_FILES_SEEDED
    if _ENV_FILES_SEEDED:
        return
    if "pytest" in sys.modules:
        _ENV_FILES_SEEDED = True
        return
    root = _settings_root()
    _seed_env_from_file(root / ".env")
    _seed_env_from_file(root / ".env.local")
    _ENV_FILES_SEEDED = True


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


def _read_token_owner() -> TokenOwner:
    value = os.environ.get("ZAKUPKI_GOV_RU_SOAP_TOKEN_OWNER", "individual").strip().lower()
    if value in {"legal", "legal_entity", "company", "organization"}:
        return "legal_entity"
    return "individual"


def _read_transport_mode(key: str, default: str) -> SoapTransportMode:
    value = os.environ.get(key, default).strip().lower()
    if value in ("gateway", "gw"):
        return "gateway"
    if value in ("disabled", "off", "0", "false"):
        return "disabled"
    return "direct"


@dataclass(frozen=True)
class EisSoapGatewaySettings:
    enabled: bool = False
    gateway_base_url: str = ""
    docs_endpoint: str = DEFAULT_INDIVIDUAL_BASE_URL
    search_endpoint: str = DEFAULT_LEGACY_BASE_URL
    docs_transport: SoapTransportMode = "direct"
    search_transport: SoapTransportMode = "disabled"
    individual_token: str = field(default="", repr=False)
    legal_entity_token: str = field(default="", repr=False)
    docs_namespace: str = DEFAULT_INDIVIDUAL_NAMESPACE
    docs_token_header: str = DEFAULT_TOKEN_HEADER_NAME
    allowed_hosts_raw: str = DEFAULT_ALLOWED_HOSTS
    user_agent: str = DEFAULT_USER_AGENT
    content_type: str = DEFAULT_CONTENT_TYPE
    soap_action_uri: str = DEFAULT_SOAP_ACTION_URI
    timeout_seconds: int = 30
    max_results: int = 10
    max_attachments: int = 20
    max_download_mb: int = 200
    debug: bool = False

    @classmethod
    def from_env(cls) -> EisSoapGatewaySettings:
        _seed_env_from_local_files()
        individual_token = os.environ.get("ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN", "").strip()
        legal_entity_token = os.environ.get("ZAKUPKI_GOV_RU_LEGAL_ENTITY_TOKEN", "").strip()
        if not individual_token:
            individual_token = os.environ.get("ZAKUPKI_GOV_RU_SOAP_TOKEN", "").strip()
        return cls(
            enabled=_read_bool("EIS_SOAP_ENABLED", False) or _read_bool("ZAKUPKI_GOV_RU_SOAP_ENABLED", False),
            gateway_base_url=os.environ.get("EIS_SOAP_GATEWAY_BASE_URL", "").strip(),
            docs_endpoint=os.environ.get("EIS_DOCS_SOAP_ENDPOINT", DEFAULT_INDIVIDUAL_BASE_URL).strip()
            or DEFAULT_INDIVIDUAL_BASE_URL,
            search_endpoint=os.environ.get("EIS_SEARCH_SOAP_ENDPOINT", DEFAULT_LEGACY_BASE_URL).strip()
            or DEFAULT_LEGACY_BASE_URL,
            docs_transport=_read_transport_mode("EIS_DOCS_SOAP_TRANSPORT", "direct"),
            search_transport=_read_transport_mode("EIS_SEARCH_SOAP_TRANSPORT", "disabled"),
            individual_token=individual_token,
            legal_entity_token=legal_entity_token,
            docs_namespace=os.environ.get("EIS_DOCS_SOAP_NAMESPACE", DEFAULT_INDIVIDUAL_NAMESPACE).strip()
            or DEFAULT_INDIVIDUAL_NAMESPACE,
            docs_token_header=os.environ.get("EIS_DOCS_SOAP_TOKEN_HEADER", DEFAULT_TOKEN_HEADER_NAME).strip()
            or DEFAULT_TOKEN_HEADER_NAME,
            allowed_hosts_raw=os.environ.get("EIS_SOAP_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS).strip()
            or DEFAULT_ALLOWED_HOSTS,
            user_agent=os.environ.get("EIS_SOAP_USER_AGENT", DEFAULT_USER_AGENT).strip() or DEFAULT_USER_AGENT,
            content_type=os.environ.get("EIS_SOAP_CONTENT_TYPE", DEFAULT_CONTENT_TYPE).strip() or DEFAULT_CONTENT_TYPE,
            soap_action_uri=os.environ.get("EIS_DOCS_SOAP_ACTION", DEFAULT_SOAP_ACTION_URI).strip()
            or DEFAULT_SOAP_ACTION_URI,
            timeout_seconds=_read_int("EIS_SOAP_TIMEOUT_SECONDS", 30),
            max_results=_read_int("EIS_SOAP_MAX_RESULTS", 10),
            max_attachments=_read_int("EIS_SOAP_MAX_ATTACHMENTS", 20),
            max_download_mb=_read_int("EIS_SOAP_MAX_DOWNLOAD_MB", 200),
            debug=_read_bool("EIS_SOAP_DEBUG", False),
        )

    @property
    def individual_token_configured(self) -> bool:
        return self.individual_token.strip().lower() not in PLACEHOLDER_TOKENS

    @property
    def legal_entity_token_configured(self) -> bool:
        return self.legal_entity_token.strip().lower() not in PLACEHOLDER_TOKENS

    @property
    def docs_available(self) -> bool:
        if not self.enabled or not self.individual_token_configured or self.docs_transport == "disabled":
            return False
        if self.docs_transport == "gateway" and not self.gateway_base_url:
            return False
        return True

    @property
    def search_available(self) -> bool:
        if not self.enabled or not self.legal_entity_token_configured or self.search_transport == "disabled":
            return False
        if self.search_transport == "gateway" and not self.gateway_base_url:
            return False
        return True

    def search_url(self) -> str:
        if self.search_transport == "gateway" and self.gateway_base_url:
            return f"{self.gateway_base_url.rstrip('/')}/eis/search"
        return self.search_endpoint

    def docs_url(self) -> str:
        if self.docs_transport == "gateway" and self.gateway_base_url:
            return f"{self.gateway_base_url.rstrip('/')}/eis/docs"
        return self.docs_endpoint

    @property
    def allowed_hosts(self) -> tuple[str, ...]:
        return tuple(item.strip().lower() for item in self.allowed_hosts_raw.split(",") if item.strip())

    def safe_status(self) -> dict[str, Any]:
        return {
            "source": "eis_soap",
            "enabled": self.enabled,
            "docs_available": self.docs_available,
            "search_available": self.search_available,
            "docs_transport": self.docs_transport,
            "search_transport": self.search_transport,
            "docs_endpoint_configured": bool(self.docs_endpoint),
            "search_endpoint_configured": bool(self.search_endpoint),
            "gateway_configured": bool(self.gateway_base_url),
            "individual_token_configured": self.individual_token_configured,
            "legal_entity_token_configured": self.legal_entity_token_configured,
            "docs_url": self.docs_url(),
            "search_url": self.search_url(),
            "timeout_seconds": self.timeout_seconds,
            "max_results": self.max_results,
        }


_token_not_configured_reason = "Токен не настроен. Добавьте ZAKUPKI_GOV_RU_INDIVIDUAL_TOKEN в .env.local"
_search_not_available_reason = "Поиск через ЕИС недоступен. Требуется токен юрлица и services-vbs endpoint."


@dataclass(frozen=True)
class ZakupkiSoapSettings:
    enabled: bool = False
    token: str = field(default="", repr=False)
    token_owner: TokenOwner = "individual"
    base_url: str = DEFAULT_LEGACY_BASE_URL
    individual_base_url: str = DEFAULT_INDIVIDUAL_BASE_URL
    individual_xsd_url: str = DEFAULT_INDIVIDUAL_XSD_URL
    individual_namespace: str = DEFAULT_INDIVIDUAL_NAMESPACE
    token_header_name: str = DEFAULT_TOKEN_HEADER_NAME
    mode: str = DEFAULT_SOAP_MODE
    disable_proxy_for_eis: bool = True
    require_direct_ru_route: bool = True
    allowed_hosts_raw: str = DEFAULT_ALLOWED_HOSTS
    user_agent: str = DEFAULT_USER_AGENT
    content_type: str = DEFAULT_CONTENT_TYPE
    use_soap_action: bool = True
    soap_action_uri: str = DEFAULT_SOAP_ACTION_URI
    search_action: str = "searchProcurements"
    details_action: str = "getProcurementDetails"
    attachments_action: str = "listAttachments"
    timeout_seconds: int = 30
    max_results: int = 10
    max_attachments: int = 20
    max_download_mb: int = 200
    trust_env_proxy: bool = False
    debug: bool = False
    _gateway_settings: EisSoapGatewaySettings | None = None

    @classmethod
    def from_env(cls) -> "ZakupkiSoapSettings":
        _seed_env_from_local_files()
        return cls(
            enabled=_read_bool("ZAKUPKI_GOV_RU_SOAP_ENABLED", False),
            token=os.environ.get("ZAKUPKI_GOV_RU_SOAP_TOKEN", "").strip(),
            token_owner=_read_token_owner(),
            base_url=os.environ.get("ZAKUPKI_GOV_RU_SOAP_BASE_URL", DEFAULT_LEGACY_BASE_URL).strip()
            or DEFAULT_LEGACY_BASE_URL,
            individual_base_url=os.environ.get("ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_BASE_URL", DEFAULT_INDIVIDUAL_BASE_URL).strip()
            or DEFAULT_INDIVIDUAL_BASE_URL,
            individual_xsd_url=os.environ.get("ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_XSD_URL", DEFAULT_INDIVIDUAL_XSD_URL).strip()
            or DEFAULT_INDIVIDUAL_XSD_URL,
            individual_namespace=os.environ.get("ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_NAMESPACE", DEFAULT_INDIVIDUAL_NAMESPACE).strip()
            or DEFAULT_INDIVIDUAL_NAMESPACE,
            token_header_name=os.environ.get("ZAKUPKI_GOV_RU_SOAP_TOKEN_HEADER_NAME", DEFAULT_TOKEN_HEADER_NAME).strip()
            or DEFAULT_TOKEN_HEADER_NAME,
            mode=os.environ.get("ZAKUPKI_GOV_RU_SOAP_MODE", DEFAULT_SOAP_MODE).strip() or DEFAULT_SOAP_MODE,
            disable_proxy_for_eis=_read_bool("ZAKUPKI_GOV_RU_SOAP_DISABLE_PROXY_FOR_EIS", True),
            require_direct_ru_route=_read_bool("ZAKUPKI_GOV_RU_SOAP_REQUIRE_DIRECT_RU_ROUTE", True),
            allowed_hosts_raw=os.environ.get("ZAKUPKI_GOV_RU_SOAP_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS).strip()
            or DEFAULT_ALLOWED_HOSTS,
            user_agent=os.environ.get("ZAKUPKI_GOV_RU_SOAP_USER_AGENT", DEFAULT_USER_AGENT).strip() or DEFAULT_USER_AGENT,
            content_type=os.environ.get("ZAKUPKI_GOV_RU_SOAP_CONTENT_TYPE", DEFAULT_CONTENT_TYPE).strip() or DEFAULT_CONTENT_TYPE,
            use_soap_action=_read_bool("ZAKUPKI_GOV_RU_SOAP_USE_SOAP_ACTION", True),
            soap_action_uri=os.environ.get("ZAKUPKI_GOV_RU_SOAP_SOAP_ACTION", DEFAULT_SOAP_ACTION_URI).strip()
            or DEFAULT_SOAP_ACTION_URI,
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

    @property
    def individual_mode(self) -> bool:
        return self.token_owner == "individual"

    @property
    def active_docs_endpoint(self) -> str:
        gw = get_eis_gateway_settings()
        if gw.docs_available:
            return gw.docs_url()
        return self.individual_base_url if self.individual_mode else self.base_url

    @property
    def allowed_hosts(self) -> tuple[str, ...]:
        return tuple(item.strip().lower() for item in self.allowed_hosts_raw.split(",") if item.strip())

    def safe_status(self) -> dict[str, Any]:
        reason = None
        if not self.token_configured:
            reason = "Источник ЕИС не настроен: добавьте токен сервиса ЕИС в .env.local"
        elif not self.enabled:
            reason = "Источник ЕИС не включён: установите ZAKUPKI_GOV_RU_SOAP_ENABLED=1"
        elif self.individual_mode:
            reason = None
        return {
            "source": "zakupki_gov_ru_getdocs_ip",
            "enabled": self.enabled,
            "configured": self.configured,
            "reason": reason,
            "token_owner": self.token_owner,
            "token_header_name": self.token_header_name,
            "mode": self.mode,
            "disable_proxy_for_eis": self.disable_proxy_for_eis,
            "require_direct_ru_route": self.require_direct_ru_route,
            "allowed_hosts": list(self.allowed_hosts),
            "user_agent": self.user_agent,
            "content_type": self.content_type,
            "use_soap_action": self.use_soap_action,
            "soap_action_uri": self.soap_action_uri,
            "individual_base_url_configured": bool(self.individual_base_url),
            "legacy_base_url_configured": bool(self.base_url),
            "individual_namespace": self.individual_namespace,
            "individual_xsd_url": self.individual_xsd_url,
            "active_docs_endpoint": self.active_docs_endpoint,
            "search_action": self.search_action,
            "details_action": self.details_action,
            "attachments_action": self.attachments_action,
            "timeout_seconds": self.timeout_seconds,
            "max_results": self.max_results,
            "max_attachments": self.max_attachments,
            "max_download_mb": self.max_download_mb,
            "trust_env_proxy": self.trust_env_proxy,
            "debug": self.debug,
            "legacy_mode_note": "services-vbs / legal entity mode / experimental",
        }


def get_eis_gateway_settings() -> EisSoapGatewaySettings:
    return EisSoapGatewaySettings.from_env()


def is_zakupki_soap_configured(settings: ZakupkiSoapSettings | None = None) -> bool:
    return (settings or get_zakupki_soap_settings()).configured


@lru_cache(maxsize=1)
def get_zakupki_soap_settings() -> ZakupkiSoapSettings:
    return ZakupkiSoapSettings.from_env()


def clear_zakupki_soap_settings_cache() -> None:
    get_zakupki_soap_settings.cache_clear()