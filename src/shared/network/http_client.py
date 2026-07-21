from __future__ import annotations

import ssl
from urllib.parse import urlparse
from urllib.request import HTTPSHandler, ProxyHandler, build_opener

import httpx

from src.shared.network.etp_trust import (
    build_ssl_context,
    policy_from_environment,
    should_bypass_proxy,
)


def create_httpx_client(url: str, *, timeout: float = 30.0) -> httpx.Client:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    policy = policy_from_environment()
    context = build_ssl_context(hostname, policy)
    trust_env = not should_bypass_proxy(hostname, policy)
    return httpx.Client(
        verify=context,
        trust_env=trust_env,
        timeout=timeout,
        follow_redirects=False,
    )


def create_urllib_context(url: str) -> tuple[ssl.SSLContext, bool]:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    policy = policy_from_environment()
    return build_ssl_context(hostname, policy), should_bypass_proxy(hostname, policy)


def create_urllib_opener(url: str):
    context, bypass_proxy = create_urllib_context(url)
    handlers = [HTTPSHandler(context=context)]
    if bypass_proxy:
        handlers.append(ProxyHandler({}))
    return build_opener(*handlers)
