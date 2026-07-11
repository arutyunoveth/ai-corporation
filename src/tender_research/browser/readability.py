"""Minimal readability-style text extraction from HTML.

Uses regex-based heuristics to extract article-like content.
For production use, consider installing readability-lxml or trafilatura.
"""
from __future__ import annotations

import re


def extract_readable_text(html: str) -> str:
    html = re.sub(r"<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "\n", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    lines = [line.strip() for line in html.split("\n") if len(line.strip()) > 40]
    return "\n\n".join(lines)
