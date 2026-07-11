from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROFILES_DIR = Path(__file__).resolve().parent / "category_profiles"

_PROFILES_CACHE: dict[str, dict[str, Any]] | None = None


def _load_all_profiles() -> dict[str, dict[str, Any]]:
    global _PROFILES_CACHE
    if _PROFILES_CACHE is not None:
        return _PROFILES_CACHE

    profiles: dict[str, dict[str, Any]] = {}
    if not _PROFILES_DIR.is_dir():
        logger.warning("Category profiles directory not found: %s", _PROFILES_DIR)
        _PROFILES_CACHE = profiles
        return profiles

    for fname in os.listdir(str(_PROFILES_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = _PROFILES_DIR / fname
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            cat = data.get("category", "")
            if cat:
                profiles[cat] = data
        except Exception:
            logger.exception("Failed to load profile %s", fname)

    _PROFILES_CACHE = profiles
    return profiles


def load_category_profile(category: str) -> dict[str, Any] | None:
    profiles = _load_all_profiles()
    return profiles.get(category)


def list_available_categories() -> list[dict[str, str]]:
    profiles = _load_all_profiles()
    return [
        {"category": p.get("category", ""), "label": p.get("label", "")}
        for p in profiles.values()
    ]


def detect_procurement_category(
    context: dict[str, Any],
    line_item_names: list[str] | None = None,
) -> str:
    profiles = _load_all_profiles()
    if not profiles:
        return "general_goods"

    text_corpus: list[str] = []

    tender = context.get("tender", {})
    title = tender.get("title", "") or ""
    text_corpus.append(title)

    for doc in context.get("documents", []):
        text_corpus.append(doc.get("file_name", "") or "")
        text_corpus.append(doc.get("role", "") or "")
        doc_text = doc.get("text", "") or ""
        if isinstance(doc_text, str) and len(doc_text) > 0:
            text_corpus.append(doc_text[:5000])

    if line_item_names:
        text_corpus.extend(line_item_names)

    combined = " ".join(text_corpus).lower()

    best_category = "general_goods"
    best_score = 0

    for cat_key, profile in profiles.items():
        signals = profile.get("signals", [])
        if not signals:
            continue
        score = 0
        for signal in signals:
            signal_lower = signal.lower()
            try:
                matches = re.findall(re.escape(signal_lower), combined)
                score += len(matches) * 2
            except re.error:
                if signal_lower in combined:
                    score += 2
        if score > best_score:
            best_score = score
            best_category = cat_key

    if best_score == 0:
        return "general_goods"

    return best_category
