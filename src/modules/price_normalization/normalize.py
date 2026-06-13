from __future__ import annotations

import re
from decimal import Decimal
from urllib.parse import urlparse, urlunparse


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().strip()
    text = re.sub(r"[^\w\s\-/]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_price(value: str | int | float | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")
    cleaned = "".join(ch for ch in raw if ch in "0123456789.-")
    if cleaned in {"", "-", ".", "-."}:
        return None
    try:
        return Decimal(cleaned)
    except Exception:
        return None


def normalize_quantity(value: str | int | float | Decimal | None) -> tuple[Decimal, list[str]]:
    parsed = normalize_price(value)
    if parsed is None or parsed <= 0:
        return Decimal("1"), ["quantity_unknown"]
    return parsed, []


def normalize_region(value: str | None) -> tuple[str | None, list[str]]:
    if not value:
        return None, ["region_unknown"]
    normalized = value.strip()
    if not normalized:
        return None, ["region_unknown"]
    return normalized, []


def normalize_delivery_price(
    value: str | int | float | Decimal | None,
    default_unknown_cost: str = "500",
) -> tuple[Decimal, list[str]]:
    parsed = normalize_price(value)
    if parsed is None:
        return Decimal(default_unknown_cost), ["delivery_unknown"]
    return parsed, []


def normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = urlparse(text)
        scheme = parsed.scheme.lower() if parsed.scheme else "https"
        netloc = parsed.netloc.lower()
        cleaned = parsed._replace(scheme=scheme, netloc=netloc, fragment="")
        return urlunparse(cleaned)
    except Exception:
        return text
