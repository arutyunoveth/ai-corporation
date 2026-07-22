from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

_GIB = 1024 ** 3


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gib(n: int | float | None) -> float | None:
    if n is None:
        return None
    return round(n / _GIB, 2)


def write_json_report(data: dict, path: str):
    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def write_relations_csv(relations: list[dict], path: str):
    if not relations:
        Path(path).write_text("schema_name,table_name,approximate_row_count,heap_bytes,indexes_bytes,total_bytes\n")
        return
    keys = ["schema_name", "table_name", "approximate_row_count", "heap_bytes", "indexes_bytes", "total_bytes"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in relations:
            w.writerow({k: r.get(k, "") for k in keys})


def write_files_csv(fs_metrics: list[dict], path: str):
    keys = [
        "root_name", "available", "logical_bytes", "allocated_bytes",
        "files_count", "directories_count", "temp_files_count", "symlinks_count",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for entry in fs_metrics:
            w.writerow({k: entry.get(k, "") for k in keys})


def write_forecast_csv(forecast: dict, path: str):
    rows = []
    for pname, pdata in forecast.get("profiles", {}).items():
        for ykey, proj in pdata.get("projections", {}).items():
            rows.append({
                "profile": pname,
                "horizon": ykey,
                "database_gib": proj.get("database_storage", {}).get("gib"),
                "file_storage_gib": proj.get("persistent_file_storage", {}).get("gib"),
                "primary_gib": proj.get("primary_storage", {}).get("gib"),
                "backup_gib": proj.get("backup_storage", {}).get("gib"),
                "temporary_gib": proj.get("temporary_storage", {}).get("gib"),
                "operational_margin_gib": proj.get("operational_margin", {}).get("gib"),
                "raw_required_gib": proj.get("raw_required", {}).get("gib"),
                "recommended_disk_gib": proj.get("recommended_disk_gib"),
                "recommended_disk_bytes": proj.get("recommended_disk_bytes"),
            })
    if not rows:
        Path(path).write_text("profile,horizon,database_gib,file_storage_gib,primary_gib,backup_gib,temporary_gib,operational_margin_gib,raw_required_gib,recommended_disk_gib,recommended_disk_bytes\n")
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def _msg(v: object) -> str:
    if v is None:
        return "N/A"
    return str(v)


def _yes(v: object) -> str:
    return "yes" if v else "no"


def _gi(v: object | None) -> str:
    if v is None:
        return "N/A"
    return f"{v:.2f} GiB" if isinstance(v, (int, float)) else str(v)


def render_snapshot_markdown(snapshot: dict) -> str:
    lines: list[str] = []
    lines.append("# Storage Capacity Snapshot Report")
    lines.append("")
    lines.append(f"- **generated_at_utc**: {snapshot.get('generated_at_utc', 'N/A')}")
    lines.append(f"- **git_commit**: {snapshot.get('git_commit', 'N/A')}")
    lines.append(f"- **schema_version**: {snapshot.get('schema_version', 'N/A')}")
    lines.append("")

    db = snapshot.get("database", {})
    lines.append("## PostgreSQL Database")
    lines.append("")
    lines.append(f"- **available**: {_yes(db.get('available'))}")
    lines.append(f"- **database_size**: {_gi(db.get('database_size_bytes'))}")
    lines.append(f"- **pgvector_version**: {_msg(db.get('pgvector_version'))}")
    lines.append(f"- **vector_columns**: {len(db.get('vector_columns', []))}")
    lines.append(f"- **row_count_kind**: {_msg(db.get('row_count_kind'))}")
    if db.get("error"):
        lines.append(f"- **error**: {db['error']}")
    warnings = db.get("warnings", [])
    if warnings:
        lines.append(f"- **warnings**: {len(warnings)}")
        for w in warnings:
            lines.append(f"  - {w}")
    lines.append("")

    rels = db.get("relations", [])
    if rels:
        total_heap = sum(r.get("heap_bytes", 0) or 0 for r in rels)
        total_idx = sum(r.get("indexes_bytes", 0) or 0 for r in rels)
        total_tbl = sum(r.get("total_bytes", 0) or 0 for r in rels)
        lines.append(f"### Relations (top 20 by size)")
        lines.append("")
        lines.append(f"- **total relations**: {len(rels)}")
        lines.append(f"- **total heap**: {_gi(total_heap)}")
        lines.append(f"- **total indexes**: {_gi(total_idx)}")
        lines.append(f"- **total size**: {_gi(total_tbl)}")
        lines.append("")
        lines.append("| # | schema | table | rows (est) | heap | indexes | total |")
        lines.append("|---|---|---|---|---|---|---|")
        for i, r in enumerate(rels[:20], 1):
            lines.append(
                f"| {i} | {r['schema_name']} | {r['table_name']} "
                f"| {_msg(r['approximate_row_count'])} "
                f"| {_gi(r['heap_bytes'])} | {_gi(r['indexes_bytes'])} "
                f"| {_gi(r['total_bytes'])} |"
            )
        lines.append("")

    fs_list = snapshot.get("filesystem", [])
    if fs_list:
        lines.append("## Filesystem Storage")
        lines.append("")
        for entry in fs_list:
            lines.append(f"### {entry['root_name']}")
            lines.append(f"- **available**: {_yes(entry.get('available'))}")
            if not entry.get("available"):
                lines.append(f"- **error**: {_msg(entry.get('error'))}")
                continue
            lines.append(f"- **logical_bytes**: {_gi(entry.get('logical_bytes'))}")
            lines.append(f"- **allocated_bytes**: {_gi(entry.get('allocated_bytes'))}")
            lines.append(f"- **files**: {entry.get('files_count', 0)}")
            lines.append(f"- **directories**: {entry.get('directories_count', 0)}")
            lines.append(f"- **temp files**: {entry.get('temp_files_count', 0)}")
            lines.append(f"- **symlinks**: {entry.get('symlinks_count', 0)}")
            ext = entry.get("bytes_by_extension", {})
            if ext:
                lines.append("  **Top extensions:**")
                for e, b in list(ext.items())[:10]:
                    lines.append(f"  - {e}: {_gi(b)}")
            lines.append("")
        lines.append("")

    backup = snapshot.get("backup", {})
    if backup:
        lines.append("## Backup")
        lines.append("")
        lines.append(f"- **available**: {_yes(backup.get('available'))}")
        if backup.get("available"):
            lines.append(f"- **total_bytes**: {_gi(backup.get('total_bytes'))}")
            lines.append(f"- **compression_ratio**: {_msg(backup.get('compression_ratio'))}")
            for comp_name, comp_val in backup.get("components", {}).items():
                lines.append(f"- {comp_name}: {_gi(comp_val.get('byte_size'))} exists={_yes(comp_val.get('exists'))}")
        if backup.get("warnings"):
            for w in backup["warnings"]:
                lines.append(f"- *warning*: {w}")
        lines.append("")

    warnings = snapshot.get("warnings", [])
    if warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def render_forecast_markdown(forecast: dict) -> str:
    lines: list[str] = []
    lines.append("# Storage Capacity Forecast Report")
    lines.append("")
    lines.append(f"- **scenario_source**: {forecast.get('scenario_source', 'N/A')}")
    lines.append(f"- **snapshot_source**: {forecast.get('snapshot_source', 'N/A')}")
    lines.append("")

    for pname, pdata in forecast.get("profiles", {}).items():
        lines.append(f"## Profile: {pname}")
        lines.append(f"*{pdata.get('description', '')}*")
        lines.append("")
        for ykey, proj in pdata.get("projections", {}).items():
            lines.append(f"### {ykey.replace('_', ' ').title()}")
            lines.append("")
            lines.append(f"- **procurements**: {proj.get('procurements', 'N/A')}")
            lines.append(f"- **analysis runs**: {proj.get('analysis_runs', 'N/A')}")
            lines.append("")
            lines.append("| Component | GiB |")
            lines.append("|---|---|")
            lines.append(f"| Database storage | {_gi(proj.get('database_storage', {}).get('gib'))} |")
            dbc = proj.get("database_storage", {}).get("components", {})
            if dbc:
                for ck, cv in dbc.items():
                    lines.append(f"| &nbsp;&nbsp;{ck} | {_gi(cv.get('gib'))} |")
            lines.append(f"| File storage | {_gi(proj.get('persistent_file_storage', {}).get('gib'))} |")
            pfc = proj.get("persistent_file_storage", {}).get("components", {})
            if pfc:
                for ck, cv in pfc.items():
                    lines.append(f"| &nbsp;&nbsp;{ck} | {_gi(cv.get('gib'))} |")
            lines.append(f"| **Primary storage** | **{_gi(proj.get('primary_storage', {}).get('gib'))}** |")
            lines.append(f"| Backup storage | {_gi(proj.get('backup_storage', {}).get('gib'))} |")
            lines.append(f"| Temporary storage | {_gi(proj.get('temporary_storage', {}).get('gib'))} |")
            lines.append(f"| Operational margin | {_gi(proj.get('operational_margin', {}).get('gib'))} |")
            lines.append(f"| **Raw required** | **{_gi(proj.get('raw_required', {}).get('gib'))}** |")
            lines.append(f"| Free space reserve | {proj.get('free_space_reserve_percent', 'N/A')}% |")
            lines.append(f"| **Recommended disk** | **{proj.get('recommended_disk_gib', 'N/A')} GiB** |")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("### Legend")
    lines.append("")
    lines.append("- **measured**: values from snapshot (real database and filesystem)")
    lines.append("- **derived**: values computed from measured data")
    lines.append("- **assumed**: values from scenario profile (example assumptions)")
    lines.append("")
    lines.append("*This report uses example scenario assumptions and does not represent final Arvectum capacity requirements.*")
    lines.append("")

    return "\n".join(lines)


def build_snapshot_json(
    db_metrics: dict,
    fs_metrics: list,
    backup_metrics: dict,
    git_commit: str,
    warnings: list[str],
) -> dict:
    return {
        "schema_version": "1.0",
        "generated_at_utc": _utc(),
        "git_commit": git_commit,
        "command_mode": "snapshot",
        "measurement_sources": {
            "database": bool(db_metrics.get("available")),
            "filesystem": len(fs_metrics) > 0,
            "backup": backup_metrics.get("available", False),
        },
        "warnings": warnings,
        "database": _strip_db_sensitive(db_metrics),
        "filesystem": _strip_fs_sensitive(fs_metrics),
        "backup": _strip_backup_sensitive(backup_metrics),
    }


def _strip_db_sensitive(db: dict) -> dict:
    safe = dict(db)
    safe.pop("dsn", None)
    safe.pop("password", None)
    safe.pop("connection_string", None)
    return safe


def _strip_fs_sensitive(fs_list: list) -> list:
    out = []
    for entry in fs_list:
        safe = dict(entry)
        safe.pop("root_path", None)
        safe.pop("absolute_path", None)
        for f in safe.get("top_files", []):
            f.pop("relative_path", None)
        out.append(safe)
    return out


def _strip_backup_sensitive(bk: dict) -> dict:
    safe = dict(bk)
    safe.pop("backup_dir", None)
    return safe


def write_snapshot_outputs(snapshot: dict, output_dir: str):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    write_json_report(snapshot, os.path.join(output_dir, "capacity_snapshot.json"))
    db = snapshot.get("database", {})
    write_relations_csv(db.get("relations", []), os.path.join(output_dir, "capacity_relations.csv"))
    write_files_csv(snapshot.get("filesystem", []), os.path.join(output_dir, "capacity_files.csv"))
    md = render_snapshot_markdown(snapshot)
    Path(os.path.join(output_dir, "capacity_report.md")).write_text(md, encoding="utf-8")


def write_forecast_outputs(forecast: dict, output_dir: str):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    write_json_report(forecast, os.path.join(output_dir, "capacity_forecast.json"))
    write_forecast_csv(forecast, os.path.join(output_dir, "capacity_forecast.csv"))
    md = render_forecast_markdown(forecast)
    Path(os.path.join(output_dir, "capacity_forecast.md")).write_text(md, encoding="utf-8")
