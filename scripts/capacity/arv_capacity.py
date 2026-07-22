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
import os
import subprocess
import sys
from pathlib import Path

from scripts.capacity.backup_reader import analyze_backup
from scripts.capacity.db_collector import collect_database_metrics
from scripts.capacity.forecast_model import run_forecast
from scripts.capacity.fs_collector import collect_filesystem_metrics
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
                warnings.append(f"database metrics collection failed: {db_metrics.get('error')}")
        else:
            db_metrics = {"available": False, "error": "no DSN provided", "warnings": ["no DSN provided"]}

    roots: dict[str, str] = {}
    if args.root:
        for r in args.root:
            if "=" not in r:
                warnings.append(f"invalid root format (expected name=path): {r}")
                continue
            name, path = r.split("=", 1)
            roots[name.strip()] = path.strip()

    fs_metrics: list[dict] = []
    if not args.no_files and roots:
        fs_metrics = collect_filesystem_metrics(roots, args.include_relative_paths)
        for entry in fs_metrics:
            if not entry.get("available"):
                warnings.append(f"filesystem root '{entry['root_name']}' unavailable: {entry.get('error')}")

    backup_metrics: dict = {"available": False}
    if args.backup_dir:
        live_artifacts = None
        for entry in fs_metrics:
            if entry.get("root_name") in ("pilot-artifacts", "artifacts", "company_agent_runs"):
                live_artifacts = entry.get("logical_bytes")
                break
        backup_metrics = analyze_backup(args.backup_dir, live_artifacts)

    snapshot = build_snapshot_json(
        db_metrics=db_metrics,
        fs_metrics=fs_metrics,
        backup_metrics=backup_metrics,
        git_commit=git_commit,
        warnings=warnings,
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
        import json
        try:
            snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"error: cannot read snapshot {args.snapshot}: {exc}", file=sys.stderr)
            return 1

    scenario_path = args.scenario
    if not os.path.isfile(scenario_path):
        print(f"error: scenario file not found: {scenario_path}", file=sys.stderr)
        return 1

    years_list = [int(y.strip()) for y in args.years.split(",") if y.strip()]
    if not years_list:
        print("error: at least one year value required", file=sys.stderr)
        return 1

    try:
        forecast = run_forecast(snapshot, scenario_path, years_list)
    except (ValueError, KeyError) as exc:
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
