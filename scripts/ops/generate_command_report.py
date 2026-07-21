#!/usr/bin/env python3
"""Run the R5 integration gate and emit auditable command/test accounting."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import time
from pathlib import Path


def _run(command: list[str], env: dict[str, str]) -> tuple[dict[str, object], str]:
    started = dt.datetime.now(dt.timezone.utc)
    started_tick = time.monotonic()
    completed = subprocess.run(command, text=True, capture_output=True, env=env)
    finished = dt.datetime.now(dt.timezone.utc)
    return {
        "command_line": " ".join(command),
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_seconds": round(time.monotonic() - started_tick, 3),
        "exit_code": completed.returncode,
    }, completed.stdout + completed.stderr


def _collected_count(output: str) -> int:
    match = re.search(r"(\d+)\s+tests?\s+collected", output)
    if not match:
        raise RuntimeError("pytest collection did not report a collected test count")
    return int(match.group(1))


def _summary_counts(output: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for key in ("passed", "skipped", "failed", "errors", "xfailed", "xpassed", "deselected"):
        word = "error" if key == "errors" else key.rstrip("s")
        match = re.search(rf"(\d+)\s+{word}s?\b", output)
        result[key] = int(match.group(1)) if match else 0
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    env = dict(os.environ)
    env["AI_CORP_SOURCE_GRAPH_MODE"] = "production"
    rows: list[dict[str, object]] = []

    collect_row, collect_output = _run(["python", "-m", "pytest", "--collect-only", "-q"], env)
    collected = _collected_count(collect_output)
    rows.append({"command": "pytest_collect", **collect_row, "collected": collected})

    for name, command in (
        ("make_check", ["make", "check"]),
        ("production_make_test", ["make", "test"]),
        ("git_diff_check", ["git", "diff", "--check"]),
        ("secret_scan", ["python", "scripts/ops/secret_scan.py"]),
        ("eis_preflight", ["make", "eis-preflight"]),
    ):
        row, output = _run(command, env)
        if name == "production_make_test":
            row.update(_summary_counts(output))
            row["collected"] = collected
            row["raw_summary_line"] = next(
                (line.strip() for line in reversed(output.splitlines()) if "passed" in line or "failed" in line),
                "",
            )
            if row["exit_code"] == 0 and not row["collected"]:
                raise RuntimeError("successful pytest run cannot have collected=0")
        rows.append({"command": name, **row})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(row["exit_code"] == 0 for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
