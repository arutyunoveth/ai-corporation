from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "yclid", "mc_cid", "mc_eid",
    "ref", "source", "from",
})


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().replace("www.", "", 1) if parsed.netloc else ""
    path = parsed.path.rstrip("/") or "/"
    query = _clean_query(parsed.query)
    fragment = ""
    cleaned = urlunparse((scheme, netloc, path, parsed.params, query, fragment))
    return cleaned


def _clean_query(query: str) -> str:
    if not query:
        return ""
    params = parse_qs(query, keep_blank_values=True)
    cleaned = {k: v for k, v in params.items() if k.lower() not in _TRACKING_PARAMS}
    if not cleaned:
        return ""
    return urlencode(cleaned, doseq=True)


_IPV4_PATTERN = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")


def is_private_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    if _IPV4_PATTERN.match(host):
        parts = host.split(".")
        if parts[0] == "10":
            return True
        if parts[0] == "172" and 16 <= int(parts[1]) <= 31:
            return True
        if parts[0] == "192" and parts[1] == "168":
            return True
    if parsed.scheme in ("file", "ftp", "chrome", "about"):
        return True
    return False
