#!/usr/bin/env python3
"""Fail on common committed credential shapes without self-matching its rules."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PATTERNS = (
    re.compile(("github" + "_pat_") + r"[A-Za-z0-9_]{20,}"),
    re.compile("gh" + "p_" + r"[A-Za-z0-9]{36}"),
    re.compile(("AK" + "IA") + r"[0-9A-Z]{16}"),
    re.compile("-----" + "BEGIN " + r"(?:RSA |EC |OPENSSH )?" + "PRIVATE KEY-----"),
)


def main() -> int:
    names = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    hits: list[str] = []
    for name in filter(None, names):
        path = Path(name)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if any(pattern.search(text) for pattern in PATTERNS):
            hits.append(name)
    if hits:
        print("possible committed secret in: " + ", ".join(hits), file=sys.stderr)
        return 1
    print("secret scan: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
