from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


TOOL_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"
EXPECTED_AGGREGATE_SHA = "8b1a1fd6d0ed994da8b8af04930951d58ba7a1d7b6ef88d256f08e143b527b58"

HORIZON_KEYS = ["1_year", "3_year", "5_year"]

SENSITIVITY_MULTIPLIERS = [0.5, 1.0, 2.0]
SENSITIVITY_PARAMS = [
    "procurements_per_month",
    "raw_document_bytes_per_procurement",
    "analysis_runs_per_procurement",
    "database_non_vector_bytes_per_procurement",
    "database_non_vector_bytes_per_run",
    "report_artifact_bytes_per_run",
    "other_artifact_bytes_per_run",
    "full_backups_retained",
    "temporary_space_peak_factor",
]

MEASURED_PARAMS = [
    "documents_per_procurement",
    "extracted_text_bytes_per_procurement",
    "chunks_per_procurement",
    "embedding_rows_per_chunk",
    "vector_dimension",
    "vector_bytes_per_component",
    "backup_compression_ratio",
]

ASSUMPTION_PARAMS = [
    "procurements_per_month",
    "analysis_runs_per_procurement",
    "raw_document_bytes_per_procurement",
    "database_non_vector_bytes_per_procurement",
    "database_non_vector_bytes_per_run",
    "report_artifact_bytes_per_run",
    "other_artifact_bytes_per_run",
    "full_backups_retained",
    "temporary_space_peak_factor",
    "operational_margin_bytes",
    "free_space_reserve_percent",
]


def _sha256(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, indent=2, sort_keys=True).encode()).hexdigest()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build final ARV-009 capacity plan")
    p.add_argument("--snapshot", required=True, type=Path)
    p.add_argument("--scenario", required=True, type=Path)
    p.add_argument("--aggregate", required=True, type=Path)
    p.add_argument("--forecast-json", required=True, type=Path)
    p.add_argument("--json-output", required=True, type=Path)
    p.add_argument("--csv-output", required=True, type=Path)
    p.add_argument("--markdown-output", required=True, type=Path)
    return p.parse_args(argv)


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _extract_components(h: dict) -> dict:
    db = h.get("database_storage", {})
    pfs = h.get("persistent_file_storage", {})
    db_comps = db.get("components", {})
    pfs_comps = pfs.get("components", {})

    raw_required_raw = h.get("raw_required", {})
    if isinstance(raw_required_raw, dict):
        raw_required = raw_required_raw.get("bytes", 0)
    else:
        raw_required = int(raw_required_raw) if raw_required_raw else 0
    recommended = h.get("recommended_disk_bytes", raw_required)
    reserve_bytes = max(0, recommended - raw_required)

    return {
        "baseline_database_bytes": db.get("baseline_bytes", 0),
        "baseline_filesystem_bytes": pfs.get("baseline_bytes", 0),
        "raw_documents_bytes": pfs_comps.get("raw_documents", {}).get("incremental_bytes", 0),
        "extracted_text_bytes": pfs_comps.get("extracted_texts", {}).get("incremental_bytes", 0),
        "database_non_vector_bytes": db_comps.get("non_vector_metadata", {}).get("incremental_bytes", 0),
        "vector_bytes": db_comps.get("vector_embeddings", {}).get("incremental_bytes", 0),
        "report_artifact_bytes": pfs_comps.get("report_artifacts", {}).get("incremental_bytes", 0),
        "other_artifact_bytes": pfs_comps.get("other_artifacts", {}).get("incremental_bytes", 0),
        "primary_storage_bytes": h.get("primary_storage", {}).get("projected_total_bytes", 0),
        "retained_backups_bytes": h.get("backup_storage", {}).get("bytes", 0),
        "temporary_storage_bytes": h.get("temporary_storage", {}).get("bytes", 0),
        "operational_margin_bytes": h.get("operational_margin", {}).get("bytes", 0),
        "free_space_reserve_bytes": reserve_bytes,
    }


def _compute_floor(gib: float) -> int:
    return -(-int(gib) // 10) * 10


def build_plan(snapshot: dict, scenario: dict, aggregate: dict, forecast: dict) -> dict:
    aggregate_sha = _sha256(aggregate)
    scenario_sha = _sha256(scenario)
    snapshot_sha = _sha256(snapshot)

    matrix = {}
    profiles_data = forecast.get("profiles", {})

    for pname in ["pilot", "commercial_mvp", "scaling"]:
        profile_forecast = profiles_data.get(pname, {}).get("projections", {})
        matrix[pname] = {}

        for hkey in HORIZON_KEYS:
            h = profile_forecast.get(hkey, {})
            if not h:
                continue

            hy = h.get("years", 0)
            proc = h.get("procurements", 0)
            runs = h.get("analysis_runs", 0)
            comps = _extract_components(h)
            total_required = h.get("recommended_disk_bytes", 0)
            total_gib = total_required / (2**30)
            floor_gib = _compute_floor(total_gib)

            largest = sorted(
                [(k, v) for k, v in comps.items() if isinstance(v, (int, float)) and v > 0],
                key=lambda x: -x[1],
            )[:5]

            matrix[pname][hkey] = {
                "profile": pname,
                "horizon_years": hy,
                "procurements_total": proc,
                "analysis_runs_total": runs,
                "components": comps,
                "total_required_bytes": total_required,
                "total_required_gib": round(total_gib, 2),
                "provisioned_floor_gib": floor_gib,
                "largest_components": largest,
            }

    ref_configs = {
        "controlled_pilot": {
            "profile": "pilot",
            "reference_horizon_years": 1,
            "description": "Controlled pilot reference configuration at 1 year",
            "reference": matrix.get("pilot", {}).get("1_year", {}),
            "other_horizons": {
                "3_year": matrix.get("pilot", {}).get("3_year", {}),
                "5_year": matrix.get("pilot", {}).get("5_year", {}),
            }
        },
        "commercial_mvp": {
            "profile": "commercial_mvp",
            "reference_horizon_years": 3,
            "description": "Commercial MVP reference configuration at 3 years",
            "reference": matrix.get("commercial_mvp", {}).get("3_year", {}),
            "other_horizons": {
                "1_year": matrix.get("commercial_mvp", {}).get("1_year", {}),
                "5_year": matrix.get("commercial_mvp", {}).get("5_year", {}),
            }
        },
        "scaling": {
            "profile": "scaling",
            "reference_horizon_years": 5,
            "description": "Full-scale production reference configuration at 5 years",
            "reference": matrix.get("scaling", {}).get("5_year", {}),
            "other_horizons": {
                "1_year": matrix.get("scaling", {}).get("1_year", {}),
                "3_year": matrix.get("scaling", {}).get("3_year", {}),
            }
        },
    }

    evidence_classification = {
        "measured": MEASURED_PARAMS,
        "measured_derived": ["backup_compression_ratio"],
        "assumption": ASSUMPTION_PARAMS,
        "note": "Classification is based on aggregate provenance and parameter notes. "
                "Parameters marked source=assumption in the scenario may have been "
                "calibrated from measurements.",
    }

    metadata_bound = {
        "note": "Metadata-only lower bound based on R3/XML calibration only. "
                "Excludes attachments, production embeddings, AnalysisRun artifacts, and LLM outputs.",
        "measured_parameters": [
            {"parameter": "documents_per_procurement", "p50": 4, "p75": 4, "p90": 5},
            {"parameter": "extracted_text_utf8_bytes_per_procurement", "p50": 121916, "p75": 144233, "p90": 162378},
            {"parameter": "chunks_per_procurement", "p50": 832, "p75": 985, "p90": 1021},
            {"parameter": "embedding_rows_per_chunk", "value": 1},
            {"parameter": "vector_dimension", "value": 256},
            {"parameter": "vector_bytes_per_component", "value": 4},
            {"parameter": "backup_compression_ratio", "B1": 0.0572, "B2": 0.0934, "forecast": 0.0934},
        ],
        "excluded": [
            "procurement attachments",
            "production AnalysisRun artifacts",
            "production embedding model dimensions",
            "real LLM outputs",
            "long-term operational growth",
        ],
        "recommendation_guard": "This lower-bound view is not a disk recommendation. "
                                "It illustrates metadata-only storage requirements without "
                                "full-document or production workload components.",
    }

    arv_010_gate = {
        "basic_contour_ready": True,
        "remaining": [
            "structured runtime metrics",
            "error monitoring",
            "jobs/queue monitoring",
            "regular restore drill",
            "CPU/RAM/load evidence",
        ],
        "note": "ARV-009 completion does not unblock VPS purchase by itself. "
                "ARV-011 still requires ARV-010 completion and CPU/RAM evidence.",
    }

    arv_011_handoff = {
        "storage_status": "ready_for_provider_comparison",
        "cpu_status": "not_measured",
        "ram_status": "not_measured",
        "runtime_metrics_status": "blocked_by_ARV_010",
        "provider_selected": False,
        "server_purchased": False,
        "note": "ARV-009 provides the disk envelope. ARV-010 provides runtime/operations evidence. "
                "ARV-011 combines storage + CPU/RAM + provider constraints. "
                "Do not purchase VPS before ARV-011.",
    }

    limitations = [
        "R3/XML metadata only — no attachments, no full document bodies",
        "Embedding provider: hashing (dim=256). Not a production embedding model",
        "LLM: stub. No generation cost measured",
        "Metadata fidelity: placeholder (truncated field values)",
        "AnalysisRun not available — pipeline subprocess used",
        "Temporary peak measurements unavailable — template defaults retained",
        "This is a planning envelope, not a production capacity guarantee",
        "Full-document calibration remains outstanding",
        "No VPS provider was selected",
        "No server was purchased",
        "CPU and RAM requirements were not determined by ARV-009",
        "No customer data was used",
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "plan_id": "ARV-009-FINAL-CAPACITY-PLAN",
        "generated_from_main_commit": snapshot.get("git_commit", ""),
        "aggregate_sha256": aggregate_sha,
        "scenario_sha256": scenario_sha,
        "snapshot_sha256": snapshot_sha,
        "forecast_tool_version": TOOL_VERSION,
        "profiles": matrix,
        "reference_configurations": ref_configs,
        "sensitivity": {},
        "metadata_only_lower_bound": metadata_bound,
        "evidence_classification": evidence_classification,
        "arv_010_gate": arv_010_gate,
        "arv_011_handoff": arv_011_handoff,
        "limitations": limitations,
    }


def _write_csv(plan: dict, path: Path):
    rows = []
    for pname in ["pilot", "commercial_mvp", "scaling"]:
        for hkey in HORIZON_KEYS:
            entry = plan.get("profiles", {}).get(pname, {}).get(hkey, {})
            if not entry:
                continue
            comps = entry.get("components", {})
            largest = entry.get("largest_components", [])
            largest_name = largest[0][0] if largest else ""

            rows.append({
                "profile": pname,
                "horizon_years": entry.get("horizon_years", ""),
                "procurements_total": entry.get("procurements_total", 0),
                "analysis_runs_total": entry.get("analysis_runs_total", 0),
                "primary_storage_gib": round(comps.get("primary_storage_bytes", 0) / (2**30), 2),
                "backups_gib": round(comps.get("retained_backups_bytes", 0) / (2**30), 2),
                "temporary_gib": round(comps.get("temporary_storage_bytes", 0) / (2**30), 2),
                "operational_margin_gib": round(comps.get("operational_margin_bytes", 0) / (2**30), 2),
                "reserve_gib": round(comps.get("free_space_reserve_bytes", 0) / (2**30), 2),
                "total_required_gib": entry.get("total_required_gib", 0),
                "provisioned_floor_gib": entry.get("provisioned_floor_gib", 0),
                "largest_component": largest_name,
                "evidence_status": "mixed",
                "provider_selected": False,
            })

    fieldnames = [
        "profile", "horizon_years", "procurements_total", "analysis_runs_total",
        "primary_storage_gib", "backups_gib", "temporary_gib",
        "operational_margin_gib", "reserve_gib", "total_required_gib",
        "provisioned_floor_gib", "largest_component", "evidence_status",
        "provider_selected",
    ]

    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _write_json(plan: dict, path: Path):
    with open(path, "w") as f:
        json.dump(plan, f, indent=2, sort_keys=True)
        f.write("\n")


def _write_markdown(plan: dict, path: Path):
    lines = [
        "# ARV-009 Final Capacity Plan",
        "",
        f"**Plan ID:** {plan['plan_id']}",
        f"**Schema version:** {plan['schema_version']}",
        f"**Main commit:** {plan['generated_from_main_commit']}",
        f"**Aggregate SHA-256:** `{plan['aggregate_sha256']}`",
        f"**Scenario SHA-256:** `{plan['scenario_sha256']}`",
        f"**Snapshot SHA-256:** `{plan['snapshot_sha256']}`",
        "",
        "## Matrix: 3 Profiles x 3 Horizons",
        "",
        "| Profile | Years | Procurements | Analysis Runs | Primary (GiB) | Backups (GiB) | Temp (GiB) | Margin (GiB) | Reserve (GiB) | Total (GiB) | Floor (GiB) |",
        "|---------|-------|-------------|---------------|--------------|--------------|-----------|-------------|--------------|------------|------------|",
    ]

    for pname in ["pilot", "commercial_mvp", "scaling"]:
        for hkey in HORIZON_KEYS:
            entry = plan.get("profiles", {}).get(pname, {}).get(hkey, {})
            if not entry:
                continue
            comps = entry.get("components", {})
            lines.append(
                f"| {pname} | {entry['horizon_years']} | {entry['procurements_total']} | "
                f"{entry['analysis_runs_total']} | "
                f"{comps.get('primary_storage_bytes', 0)/(2**30):.1f} | "
                f"{comps.get('retained_backups_bytes', 0)/(2**30):.1f} | "
                f"{comps.get('temporary_storage_bytes', 0)/(2**30):.1f} | "
                f"{comps.get('operational_margin_bytes', 0)/(2**30):.1f} | "
                f"{comps.get('free_space_reserve_bytes', 0)/(2**30):.1f} | "
                f"{entry['total_required_gib']:.1f} | {entry['provisioned_floor_gib']} |"
            )

    lines.append("")
    lines.append("## Reference Configurations")
    lines.append("")

    for rname, rcfg in plan.get("reference_configurations", {}).items():
        ref = rcfg.get("reference", {})
        lines.append(f"### {rname}")
        lines.append(f"**Profile:** {rcfg['profile']}")
        lines.append(f"**Reference horizon:** {rcfg['reference_horizon_years']} year(s)")
        lines.append(f"**Total required:** {ref.get('total_required_gib', 0)} GiB")
        lines.append(f"**Provisioned floor:** {ref.get('provisioned_floor_gib', 0)} GiB")
        lines.append("")
        lines.append("| Component | Bytes | GiB |")
        lines.append("|-----------|-------|-----|")
        comps = ref.get("components", {})
        for cname in [
            "baseline_database_bytes", "baseline_filesystem_bytes", "raw_documents_bytes",
            "extracted_text_bytes", "database_non_vector_bytes", "vector_bytes",
            "report_artifact_bytes", "other_artifact_bytes", "primary_storage_bytes",
            "retained_backups_bytes", "temporary_storage_bytes", "operational_margin_bytes",
            "free_space_reserve_bytes",
        ]:
            val = comps.get(cname, 0)
            if isinstance(val, (int, float)) and val > 0:
                lines.append(f"| {cname} | {val} | {val/(2**30):.2f} |")
        lines.append("")

    lines.append("## Limitations")
    lines.append("")
    for lim in plan.get("limitations", []):
        lines.append(f"- {lim}")
    lines.append("")

    lines.append("## ARV-011 Handoff")
    lines.append("")
    ho = plan.get("arv_011_handoff", {})
    for key, val in ho.items():
        lines.append(f"- {key}: {val}")
    lines.append("")
    lines.append("---")
    lines.append("*This is a planning envelope, not a production capacity guarantee.*")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    snapshot = _load_json(args.snapshot)
    scenario = _load_json(args.scenario)
    aggregate = _load_json(args.aggregate)
    forecast = _load_json(args.forecast_json)

    aggregate_sha = _sha256(aggregate)

    if aggregate_sha != EXPECTED_AGGREGATE_SHA:
        print(f"ERROR: aggregate SHA mismatch: got {aggregate_sha}, expected {EXPECTED_AGGREGATE_SHA}", file=sys.stderr)
        return 1

    plan = build_plan(snapshot, scenario, aggregate, forecast)

    _write_json(plan, args.json_output)
    _write_csv(plan, args.csv_output)
    _write_markdown(plan, args.markdown_output)

    json_dump = json.dumps(plan, indent=2, sort_keys=True)
    output_sha = hashlib.sha256(json_dump.encode()).hexdigest()
    print(f"Plan written to {args.json_output}")
    print(f"CSV written to {args.csv_output}")
    print(f"Markdown written to {args.markdown_output}")
    print(f"Output SHA-256: {output_sha}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
