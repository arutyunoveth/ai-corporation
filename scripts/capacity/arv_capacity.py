#!/usr/bin/env python3
"""
ARV-009 Storage Capacity Toolkit

Read-only toolkit for measuring PostgreSQL/pgvector, filesystem artifacts,
backup analysis, and forecasting disk requirements.

Usage:
  python scripts/capacity/arv_capacity.py snapshot --help
  python scripts/capacity/arv_capacity.py forecast --help
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.capacity.backup_reader import (
    analyze_backup,
    resolve_backup_source_names,
)
from scripts.capacity.db_collector import collect_database_metrics
from scripts.capacity.forecast_model import run_forecast
from scripts.capacity.fs_collector import (
    collect_filesystem_metrics,
    resolve_backup_source_bytes,
)
from scripts.capacity.report_renderer import (
    build_snapshot_json,
    write_forecast_outputs,
    write_snapshot_outputs,
)


def _resolve_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def cmd_snapshot(args: argparse.Namespace) -> int:
    warnings: list[str] = []
    git_commit = _resolve_git_commit()

    db_metrics = {"available": False}
    if not args.no_db:
        raw_dsn: str | None = None
        if args.database_url_env:
            raw_dsn = os.environ.get(args.database_url_env)
            if not raw_dsn:
                warnings.append(
                    f"env {args.database_url_env} not set; database metrics skipped"
                )
        if raw_dsn:
            db_metrics = collect_database_metrics(raw_dsn)
            if not db_metrics.get("available"):
                warnings.append("database metrics collection failed")
        else:
            db_metrics = {"available": False, "error": {"code": "no_dsn", "error_type": "ConfigError"}}

    roots: dict[str, str] = {}
    if args.root:
        for r in args.root:
            if "=" not in r:
                warnings.append("invalid root format")
                continue
            name, path = r.split("=", 1)
            roots[name.strip()] = path.strip()

    fs_metrics: list[dict] = []
    if not args.no_files and roots:
        fs_metrics = collect_filesystem_metrics(roots, args.include_relative_paths)
        for entry in fs_metrics:
            if not entry.get("available"):
                warnings.append(
                    f"filesystem root '{entry['root_name']}' unavailable"
                )

    backup_metrics: dict = {"available": False}
    if args.backup_dir:
        source_names = resolve_backup_source_names(args.backup_source_root)
        source_name_set = set(source_names)
        live_archive_source_bytes = resolve_backup_source_bytes(fs_metrics, source_name_set)
        if live_archive_source_bytes is None:
            warnings.append(
                "backup compression ratio not computed: one or more backup source roots missing"
            )
        backup_metrics = analyze_backup(args.backup_dir, live_archive_source_bytes)

    privacy_flags = {"include_relative_paths": args.include_relative_paths}

    snapshot = build_snapshot_json(
        db_metrics=db_metrics,
        fs_metrics=fs_metrics,
        backup_metrics=backup_metrics,
        git_commit=git_commit,
        warnings=warnings,
        privacy_flags=privacy_flags,
    )

    output_dir = args.output_dir or os.path.join(
        os.environ.get("HOME", "/tmp"), "arvectum-capacity", "snapshot"
    )
    write_snapshot_outputs(snapshot, output_dir)
    print(f"snapshot written to {output_dir}/")
    return 0


def cmd_forecast(args: argparse.Namespace) -> int:
    snapshot = None
    if args.snapshot:
        try:
            snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"error: cannot read snapshot: {exc}", file=sys.stderr)
            return 1

    scenario_path = args.scenario
    if not os.path.isfile(scenario_path):
        print(f"error: scenario file not found: {scenario_path}", file=sys.stderr)
        return 1

    raw_years = [y.strip() for y in args.years.split(",") if y.strip()]
    years_list: list[int] = []
    seen: set[int] = set()
    for y in raw_years:
        try:
            yv = int(y)
        except ValueError:
            print(f"error: invalid year value: {y}", file=sys.stderr)
            return 1
        if yv <= 0:
            print(f"error: year must be positive: {yv}", file=sys.stderr)
            return 1
        if yv in seen:
            print(f"error: duplicate year: {yv}", file=sys.stderr)
            return 1
        seen.add(yv)
        years_list.append(yv)
    if not years_list:
        print("error: at least one year value required", file=sys.stderr)
        return 1

    try:
        forecast = run_forecast(snapshot, scenario_path, years_list)
    except (ValueError, KeyError, ZeroDivisionError) as exc:
        print(f"error: forecast computation failed: {exc}", file=sys.stderr)
        return 1

    output_dir = args.output_dir or os.path.join(
        os.environ.get("HOME", "/tmp"), "arvectum-capacity", "forecast"
    )
    write_forecast_outputs(forecast, output_dir)
    print(f"forecast written to {output_dir}/")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ARV-009 Storage Capacity Toolkit",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="Collect live storage snapshot")
    snap.add_argument(
        "--database-url-env",
        default="AI_CORP_DATABASE_URL",
        help="Environment variable name holding the PostgreSQL DSN (default: AI_CORP_DATABASE_URL)",
    )
    snap.add_argument(
        "--root",
        action="append",
        default=[],
        help="Root directory name=path, can be specified multiple times",
    )
    snap.add_argument("--backup-dir", default=None, help="Path to existing backup directory")
    snap.add_argument(
        "--backup-source-root",
        action="append",
        default=None,
        help="Root name for backup source bytes calculation (repeatable). Falls back to defaults if not provided.",
    )
    snap.add_argument("--output-dir", default=None, help="Output directory for reports")
    snap.add_argument("--no-db", action="store_true", help="Skip database collection")
    snap.add_argument("--no-files", action="store_true", help="Skip filesystem collection")
    snap.add_argument(
        "--include-relative-paths",
        action="store_true",
        help="Include relative paths in top files listing (off by default)",
    )
    snap.set_defaults(func=cmd_snapshot)

    fore = sub.add_parser("forecast", help="Run storage forecast")
    fore.add_argument(
        "--snapshot",
        default=None,
        help="Path to capacity_snapshot.json (optional, for measured baseline)",
    )
    fore.add_argument(
        "--scenario",
        required=True,
        help="Path to scenario JSON file (e.g., samples/capacity/scenarios.example.json)",
    )
    fore.add_argument(
        "--years",
        default="1,3,5",
        help="Comma-separated year horizons (default: 1,3,5)",
    )
    fore.add_argument("--output-dir", default=None, help="Output directory for reports")
    fore.set_defaults(func=cmd_forecast)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
