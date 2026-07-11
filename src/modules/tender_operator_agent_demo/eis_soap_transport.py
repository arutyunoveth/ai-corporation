from __future__ import annotations

import ssl
import urllib.request
from dataclasses import dataclass
from enum import Enum
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from src.modules.tender_operator_agent_demo.settings import EisSoapGatewaySettings


class SoapCapability(Enum):
    DOCS = "docs"
    SEARCH = "search"


class TransportStatus(Enum):
    AVAILABLE = "available"
    DISABLED = "disabled"
    GATEWAY_ONLY = "gateway_only"
    TLS_INCOMPATIBLE = "tls_incompatible"
    GATEWAY_DISABLED = "gateway_disabled"


@dataclass(frozen=True)
class TransportResult:
    status: TransportStatus
    xml: str | None = None
    error: str | None = None
    http_status: int | None = None


DOCS_HELP_TEXT = (
    "getDocsIP: рабочий dev/docs путь. Использует TLSv1.2 (ECDHE-RSA-AES256-GCM-SHA384) "
    "с int.zakupki.gov.ru:443. Работает на macOS/OpenSSL. "
    "Поддерживает: getDocsByReestrNumberRequest, getDocsByOrgRegionRequest, getNsiRequest."
)

SEARCH_HELP_TEXT = (
    "services-vbs: production path. Требует ГОСТ-совместимый TLS-клиент (КриптоПро, "
    "ГОСТ TLS termination на gateway). int44.zakupki.gov.ru сбрасывает не-ГОСТ "
    "TLS-соединения на уровне handshake. "
    "На macOS/OpenSSL НЕ РАБОТАЕТ из-за 'Connection reset by peer' при TLS handshake. "
    'Используйте EIS_SOAP_TRANSPORT=gateway и EIS_SOAP_GATEWAY_BASE_URL для production.'
)

EIS_44FZ_HOST = "zakupki.gov.ru"


def _is_allowed_eis_host(hostname: str, allowed_hosts: tuple[str, ...]) -> bool:
    for host in allowed_hosts:
        normalized = host.strip().lower()
        if not normalized:
            continue
        if normalized.startswith("."):
            if hostname.endswith(normalized):
                return True
            continue
        if hostname == normalized or hostname.endswith(f".{normalized}"):
            return True
    return False


def _build_opener(settings: EisSoapGatewaySettings, target_url: str) -> urllib.request.OpenerDirector:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    hostname = (urlparse(target_url).hostname or "").lower()
    target_allowed = _is_allowed_eis_host(hostname, settings.allowed_hosts)
    if target_allowed:
        return build_opener(HTTPSHandler(context=ssl_ctx), ProxyHandler({}))
    return build_opener(HTTPSHandler(context=ssl_ctx), ProxyHandler({}))


def transport_status(settings: EisSoapGatewaySettings, capability: SoapCapability) -> TransportStatus:
    if capability == SoapCapability.DOCS:
        if settings.docs_transport == "disabled":
            return TransportStatus.DISABLED
        if settings.docs_transport == "gateway" and not settings.gateway_base_url:
            return TransportStatus.GATEWAY_ONLY
        if settings.docs_transport == "direct":
            return TransportStatus.AVAILABLE
        return TransportStatus.GATEWAY_ONLY
    else:
        if settings.search_transport == "disabled":
            return TransportStatus.DISABLED
        if settings.search_transport == "gateway":
            if settings.gateway_base_url:
                return TransportStatus.AVAILABLE
            return TransportStatus.GATEWAY_ONLY
        return TransportStatus.TLS_INCOMPATIBLE


def post_soap(
    settings: EisSoapGatewaySettings,
    envelope: str,
    *,
    capability: SoapCapability,
    soap_action: str | None = None,
) -> TransportResult:
    if capability == SoapCapability.DOCS:
        if settings.docs_transport == "disabled":
            return TransportResult(TransportStatus.DISABLED, error="getDocsIP transport disabled")
        endpoint = settings.docs_url()
    else:
        if settings.search_transport == "disabled":
            return TransportResult(TransportStatus.DISABLED, error="services-vbs search disabled")
        if settings.search_transport == "direct":
            return TransportResult(TransportStatus.TLS_INCOMPATIBLE, error="services-vbs недоступен через прямой TLS на macOS. Используйте EIS_SOAP_SEARCH_TRANSPORT=gateway")
        endpoint = settings.search_url()

    headers = {
        "Content-Type": settings.content_type,
        "User-Agent": settings.user_agent,
    }
    if soap_action:
        headers["SOAPAction"] = soap_action

    request = Request(endpoint, data=envelope.encode("utf-8"), headers=headers, method="POST")
    opener = _build_opener(settings, endpoint)

    try:
        with opener.open(request, timeout=settings.timeout_seconds) as response:
            xml = response.read().decode("utf-8", errors="replace")
            return TransportResult(
                status=TransportStatus.AVAILABLE,
                xml=xml,
                http_status=response.status,
            )
    except HTTPError as exc:
        return TransportResult(
            status=TransportStatus.AVAILABLE,
            error=f"HTTP {exc.code}",
            http_status=exc.code,
        )
    except URLError as exc:
        reason = str(exc.reason) if hasattr(exc, "reason") else str(exc)
        if "reset" in reason.lower() and capability == SoapCapability.SEARCH:
            return TransportResult(
                TransportStatus.TLS_INCOMPATIBLE,
                error=f"services-vbs: Connection reset by peer. {SEARCH_HELP_TEXT}",
            )
        return TransportResult(
            TransportStatus.AVAILABLE,
            error=reason,
        )
    except Exception as exc:
        return TransportResult(
            TransportStatus.AVAILABLE,
            error=str(exc),
        )