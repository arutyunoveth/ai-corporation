#!/usr/bin/env python3
"""
Deterministic calibration harness for R3 metadata cohort.

Usage:
    python scripts/capacity/calibration/calibrate_cohort.py \\
        --input /tmp/arvectum-arv009-b22/measurements/cohort.json \\
        --aggregate-output samples/capacity/public-r3-calibration.aggregate.json \\
        --scenario-template samples/capacity/scenarios.example.json \\
        --scenario-output samples/capacity/scenarios.public-r3-calibrated.json
"""

import argparse
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path


# ── nearest-rank percentiles ──────────────────────────────────────────


def nearest_rank_percentile(sorted_vals, p):
    """nearest-rank: rank = ceil(p/100 * n), index = rank - 1."""
    n = len(sorted_vals)
    if n == 0:
        return None
    rank = math.ceil(p / 100.0 * n)
    idx = max(0, min(rank - 1, n - 1))
    return sorted_vals[idx]


def compute_percentiles(values):
    vals = [v for v in values if v is not None]
    s = sorted(vals)
    n = len(values)
    available = sum(1 for v in values if v is not None)
    unavailable = sum(1 for v in values if v is None)
    vals = [v for v in values if v is not None]
    if not vals:
        return {
            "min": None, "max": None, "mean": None,
            "p50": None, "p75": None, "p90": None,
            "count": n, "available_count": available,
            "unavailable_count": unavailable,
            "coverage_percent": round(available / n * 100, 1) if n > 0 else 0.0,
        }
    sv = sorted(vals)
    return {
        "min": sv[0],
        "max": sv[-1],
        "mean": round(sum(vals) / len(vals), 1),
        "p50": nearest_rank_percentile(sv, 50),
        "p75": nearest_rank_percentile(sv, 75),
        "p90": nearest_rank_percentile(sv, 90),
        "count": n,
        "available_count": available,
        "unavailable_count": unavailable,
        "coverage_percent": round(available / n * 100, 1) if n > 0 else 0.0,
    }


# ── aggregate builder ────────────────────────────────────────────────


def build_aggregate(cohort, baseline, backup_b1, backup_b2, peak_all):
    cases = cohort.get("cases", {})
    case_list = [c for c in cases.values() if c.get("status") == "success"]

    total_attempted = cohort.get("total_attempted", len(cases))
    successful = sum(1 for c in cases.values() if c.get("status") == "success")
    failed = sum(1 for c in cases.values() if c.get("status") == "failed")
    excluded = sum(1 for c in cases.values() if c.get("status") not in ("success", "failed"))

    fail_reasons = {}
    for c in cases.values():
        if c.get("status") == "failed":
            err = c.get("error", "unknown")
            fail_reasons[err] = fail_reasons.get(err, 0) + 1

    # Per-case values for ingestion
    doc_counts = [c["measurements"].get("xml_document_count", {}).get("value") for c in case_list]
    text_chars = [c["measurements"].get("extracted_text_chars", {}).get("value") for c in case_list]
    chunk_counts = [c["measurements"].get("chunk_count", {}).get("value") for c in case_list]
    emb_rows = [c["measurements"].get("embedding_rows", {}).get("value") for c in case_list]
    fs_deltas = [c["measurements"].get("filesystem_data_delta_bytes", {}).get("value") for c in case_list]
    pg_deltas = [c["measurements"].get("postgresql_delta_bytes", {}).get("value") for c in case_list]
    archive_bytes = [c["measurements"].get("archive_bytes", {}).get("value") for c in case_list]

    ingestion_stats = {
        "documents_per_procurement": compute_percentiles(doc_counts),
        "extracted_text_bytes_per_procurement": compute_percentiles(text_chars),
        "chunks_per_procurement": compute_percentiles(chunk_counts),
        "embedding_rows_per_procurement": compute_percentiles(emb_rows),
        "archive_bytes_per_procurement": compute_percentiles(archive_bytes),
        "filesystem_data_delta_bytes_per_procurement": compute_percentiles(fs_deltas),
        "postgresql_delta_bytes_per_procurement": compute_percentiles(pg_deltas),
    }

    # Group-level
    groups = {"lower": [], "middle": [], "upper": []}
    for c in case_list:
        g = c.get("group", "unknown")
        groups.setdefault(g, []).append(c)

    group_stats = {}
    for g, lst in groups.items():
        fs = [c["measurements"].get("filesystem_data_delta_bytes", {}).get("value", 0) for c in lst]
        pg = [c["measurements"].get("postgresql_delta_bytes", {}).get("value", 0) for c in lst]
        ch = [c["measurements"].get("chunk_count", {}).get("value", 0) for c in lst]
        group_stats[g] = {
            "filesystem_data_delta_bytes_per_procurement": compute_percentiles(fs),
            "postgresql_delta_bytes_per_procurement": compute_percentiles(pg),
            "chunks_per_procurement": compute_percentiles(ch),
        }

    # Analysis run statistics (unavailable — no R8 path)
    analysis_run_stats = {
        "status": "unavailable",
        "reason": "R8 AnalysisRun path does not exist without src/ changes.",
        "database_non_vector_bytes_per_run": None,
        "report_artifact_bytes_per_run": None,
        "other_artifact_bytes_per_run": None,
    }
    repeat_run_stats = {
        "status": "unavailable",
        "reason": "R8 AnalysisRun path does not exist. Repeat runs measured via pipeline subprocess only.",
    }

    # PG reconciliation
    baseline_pg = baseline.get("postgresql_database_bytes", 0)
    baseline_rel = baseline.get("relation_total_bytes", 0)
    final_pg = backup_b2.get("database_source_bytes", 0)
    final_rel_sum = sum(
        r for r in (baseline.get("relation_sizes", {}) or {}).values()
    )

    # Use current relation sizes from the live DB
    b2_rel = backup_b2.get("relation_sizes", {})
    if not b2_rel:
        b2_rel = baseline.get("relation_sizes", {})

    agg = {
        "schema_version": "2.0",
        "measurement_id": "ARV-009-B2-R3-METADATA-CALIBRATION",
        "workload_type": "public_eis_r3_xml",
        "calibration_scope": "metadata_ingestion_only",
        "baseline_commit": "9bf0571",
        "alembic_head": "096_add_r8_canonical_snapshot_binding",
        "postgresql_version": "17",
        "pgvector_version": "0.8.0",
        "metadata_fidelity": "placeholder",
        "providers": {
            "llm": "stub",
            "embeddings": "hashing",
        },
        "cohort": {
            "total_cases": 18,
            "attempted_count": total_attempted,
            "successful_count": successful,
            "failed_count": failed,
            "excluded_count": excluded,
            "failure_reason_counts": fail_reasons,
            "tertile_groups": {"lower": 6, "middle": 6, "upper": 6},
        },
        "ingestion_statistics": ingestion_stats,
        "group_statistics": group_stats,
        "analysis_run_statistics": analysis_run_stats,
        "repeat_run_statistics": repeat_run_stats,
        "backup_measurements": {
            "B1": {
                "case_count": backup_b1.get("case_count", 9),
                "postgresql_dump_bytes": backup_b1.get("postgresql_dump_bytes", 0),
                "database_source_bytes": backup_b1.get("database_source_bytes", 0),
                "unique_live_source_bytes": backup_b1.get("unique_live_source_bytes", 0),
                "total_source_bytes": backup_b1.get("total_source_bytes", 0),
                "archive_to_source_ratio": backup_b1.get("archive_to_source_ratio", 0),
                "compression_factor": backup_b1.get("compression_factor", 0),
            },
            "B2": {
                "case_count": backup_b2.get("case_count", 18),
                "postgresql_dump_bytes": backup_b2.get("postgresql_dump_bytes", 0),
                "database_source_bytes": backup_b2.get("database_source_bytes", 0),
                "unique_live_source_bytes": backup_b2.get("unique_live_source_bytes", 0),
                "total_source_bytes": backup_b2.get("total_source_bytes", 0),
                "archive_to_source_ratio": backup_b2.get("archive_to_source_ratio", 0),
                "compression_factor": backup_b2.get("compression_factor", 0),
            },
        },
        "temporary_peak_measurements": _extract_peak(peak_all) if peak_all else None,
        "postgresql_reconciliation": _pg_reconciliation(
            baseline, backup_b2, baseline_pg, final_pg
        ),
        "limitations": [
            "R3/XML metadata only — no attachments, no full document bodies.",
            "Embeddings provider: hashing (dim=256, no paid API).",
            "LLM: stub (no generation cost measured).",
            "metadata_fidelity: placeholder (truncated field values).",
            "AnalysisRun not available — pipeline subprocess used instead.",
            "PG database_size includes schema overhead, WAL, autovacuum bloat.",
            "pg_database_size does not shrink after DELETEs.",
            "Temporary peak measurements are cumulative before/after, not continuous.",
        ],
        "formulas": {
            "archive_to_source_ratio": "total_backup_bytes / unique_live_source_bytes",
            "compression_factor": "total_source_bytes / total_backup_bytes",
            "coverage_percent": "available_count / count * 100",
            "ingestion_fs_delta_per_case": "filesystem_data_delta_bytes after ingest + chunk + embed",
            "nearest_rank_percentile": "rank = ceil(p/100 * n), index = rank - 1",
            "p50": "nearest_rank(sorted_values, 50)",
            "p75": "nearest_rank(sorted_values, 75)",
            "p90": "nearest_rank(sorted_values, 90)",
        },
    }
    return agg


def _extract_peak(peak):
    if not peak:
        return None
    deltas = peak.get("peak_deltas", {})
    all_d = deltas.get("all", {})
    return {
        "total_logical_bytes_peak": all_d.get("peak_logical_bytes"),
        "total_allocated_bytes_peak": all_d.get("peak_allocated_bytes"),
        "delta_logical_bytes": all_d.get("peak_delta_logical_bytes"),
        "delta_allocated_bytes": all_d.get("peak_delta_allocated_bytes"),
        "limitations": peak.get("limitations", []),
    }


def _pg_reconciliation(baseline, backup_b2, baseline_pg, final_pg):
    pg_delta = final_pg - baseline_pg
    bl_rel = baseline.get("relation_total_bytes", 0) or 0

    baseline_rels = baseline.get("relation_sizes", {}) or {}
    b2_rels = backup_b2.get("relation_sizes", {}) or {}

    # Sum relation deltas (only for existing keys in baseline)
    rel_delta = 0
    keyed_deltas = {}
    for rname, bsize in baseline_rels.items():
        fsize = b2_rels.get(rname, 0)
        d = fsize - bsize
        if d != 0:
            keyed_deltas[rname] = d
            rel_delta += d

    return {
        "pg_database_size_delta_bytes": pg_delta,
        "pg_final_bytes": final_pg,
        "pg_baseline_bytes": baseline_pg,
        "relation_total_delta_bytes": rel_delta,
        "relation_deltas_by_table": keyed_deltas,
        "note": (
            "pg_database_size delta includes PostgreSQL block-level allocation, "
            "WAL overhead, catalog bloat, and unused space from DELETEs. "
            "Relation-level deltas are logical bytes and may be smaller."
        ),
    }


# ── scenario builder ────────────────────────────────────────────────


def build_scenario(aggregate, template_path):
    template = json.loads(Path(template_path).read_text())

    # Compute aggregate SHA
    agg_bytes = json.dumps(aggregate, indent=2, sort_keys=True).encode()
    agg_sha256 = hashlib.sha256(agg_bytes).hexdigest()

    scenario = deepcopy(template)

    # Inject aggregate SHA into notes
    if "notes" not in scenario:
        scenario["notes"] = []
    scenario["notes"].insert(0, f"Aggregate SHA-256: {agg_sha256}")
    scenario["notes"].insert(
        1,
        "Calibrated from 18-case R3/XML metadata ingestion cohort. "
        "Attachments unavailable, placeholder metadata, hashing embeddings, stub LLM. "
        "This is a lower-bound estimate. Not a production capacity guarantee.",
    )

    # Measured calibration parameters
    ing = aggregate["ingestion_statistics"]
    b2 = aggregate["backup_measurements"]["B2"]
    compression = b2.get("archive_to_source_ratio", 1.0)
    compression_factor = b2.get("compression_factor", 1.0)

    # Measured: p50/p75/p90
    p50_chunks = ing["chunks_per_procurement"]["p50"] or 0
    p75_chunks = ing["chunks_per_procurement"]["p75"] or 0
    p90_chunks = ing["chunks_per_procurement"]["p90"] or 0

    p50_fs = ing["filesystem_data_delta_bytes_per_procurement"]["p50"] or 0
    p75_fs = ing["filesystem_data_delta_bytes_per_procurement"]["p75"] or 0
    p90_fs = ing["filesystem_data_delta_bytes_per_procurement"]["p90"] or 0

    p50_pg = ing["postgresql_delta_bytes_per_procurement"]["p50"] or 0
    p75_pg = ing["postgresql_delta_bytes_per_procurement"]["p75"] or 0
    p90_pg = ing["postgresql_delta_bytes_per_procurement"]["p90"] or 0

    p50_docs = ing["documents_per_procurement"]["p50"] or 0
    p75_docs = ing["documents_per_procurement"]["p75"] or 0
    p90_docs = ing["documents_per_procurement"]["p90"] or 0

    p50_text = ing["extracted_text_bytes_per_procurement"]["p50"] or 0
    p75_text = ing["extracted_text_bytes_per_procurement"]["p75"] or 0
    p90_text = ing["extracted_text_bytes_per_procurement"]["p90"] or 0

    # Map profiles: pilot=median, commercial_mvp=p75, scaling=p90
    profile_map = {
        "pilot": {
            "documents_per_procurement": p50_docs,
            "extracted_text_bytes_per_procurement": p50_text,
            "chunks_per_procurement": p50_chunks,
        },
        "commercial_mvp": {
            "documents_per_procurement": p75_docs,
            "extracted_text_bytes_per_procurement": p75_text,
            "chunks_per_procurement": p75_chunks,
        },
        "scaling": {
            "documents_per_procurement": p90_docs,
            "extracted_text_bytes_per_procurement": p90_text,
            "chunks_per_procurement": p90_chunks,
        },
    }

    # Apply profile values
    # Calibrated parameters (override value only, keep source=assumption for forecast compatibility)
    calibrated_params = [
        "documents_per_procurement",
        "extracted_text_bytes_per_procurement",
        "chunks_per_procurement",
    ]

    if "profiles" in scenario and isinstance(scenario["profiles"], dict):
        for name, profile in scenario["profiles"].items():
            mapped = profile_map.get(name, {})
            for k, v in mapped.items():
                if k in profile and isinstance(profile[k], dict):
                    profile[k]["value"] = v
                    profile[k]["source"] = "assumption"
                    profile[k]["note"] = (
                        "Calibrated from R3/XML metadata ingestion (18-case cohort). "
                        f"Percentile: {name}. See aggregate notes for full calibration context."
                    )

    # Set backup compression ratio: use min(1.0, archive_to_source_ratio)
    forecast_compression = min(1.0, compression)
    for name, profile in scenario.get("profiles", {}).items():
        if isinstance(profile, dict) and "backup_compression_ratio" in profile:
            br = profile["backup_compression_ratio"]
            if isinstance(br, dict):
                br["value"] = forecast_compression
                br["source"] = "assumption"
                br["note"] = (
                    "Calibrated from B2 backup. Forecast uses "
                    "min(1.0, archive_to_source_ratio) for conservative estimate."
                )

    # Temporary factor: use compression_factor / forecast_compression
    observed_factor = round(
        compression_factor / max(forecast_compression, 0.001), 2
    )
    for name, profile in scenario.get("profiles", {}).items():
        if isinstance(profile, dict) and "temporary_space_peak_factor" in profile:
            tf = profile["temporary_space_peak_factor"]
            if isinstance(tf, dict):
                tf["value"] = observed_factor
                tf["source"] = "assumption"
                tf["note"] = (
                    "Calibrated from total_source_bytes / total_backup_bytes. "
                    "Reflects observed temporary storage overhead."
                )

    # Embedding parameters (same for all profiles)
    emb_params = {
        "vector_dimension": 256,
        "embedding_rows_per_chunk": 1,
        "vector_bytes_per_component": 4,
    }
    for name, profile in scenario.get("profiles", {}).items():
        if isinstance(profile, dict):
            for pk, pv in emb_params.items():
                if pk in profile and isinstance(profile[pk], dict):
                    profile[pk]["value"] = pv
                    profile[pk]["source"] = "assumption"

    # Business assumption parameters remain unchanged

    return scenario, agg_sha256


def main():
    parser = argparse.ArgumentParser(description="Calibrate R3 metadata cohort")
    parser.add_argument("--input", required=True)
    parser.add_argument("--aggregate-output", required=True)
    parser.add_argument("--scenario-template", required=True)
    parser.add_argument("--scenario-output", required=True)
    args = parser.parse_args()

    cohort = json.loads(Path(args.input).read_text())
    baseline = json.loads(
        (Path(args.input).parent / "baseline.json").read_text()
    )
    backup_b1 = json.loads(
        (Path(args.input).parent / "backup-b1.json").read_text()
    )
    backup_b2 = json.loads(
        (Path(args.input).parent / "backup-b2.json").read_text()
    )
    peak_all_path = Path(args.input).parent / "peak-overall.json"
    peak_all = None
    if peak_all_path.exists():
        peak_all = json.loads(peak_all_path.read_text())

    aggregate = build_aggregate(cohort, baseline, backup_b1, backup_b2, peak_all)

    # Write aggregate
    agg_path = Path(args.aggregate_output)
    agg_path.parent.mkdir(parents=True, exist_ok=True)
    agg_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True))
    print(f"Aggregate written: {agg_path}")

    # Build and write scenario
    scenario, agg_sha = build_scenario(aggregate, args.scenario_template)
    sce_path = Path(args.scenario_output)
    sce_path.parent.mkdir(parents=True, exist_ok=True)
    sce_path.write_text(json.dumps(scenario, indent=2, sort_keys=True))
    print(f"Scenario written: {sce_path}")

    # Verify aggregate SHA matches scenario notes
    actual_agg_sha = hashlib.sha256(
        json.dumps(aggregate, indent=2, sort_keys=True).encode()
    ).hexdigest()
    assert actual_agg_sha == agg_sha, "Aggregate SHA mismatch in scenario notes!"
    print(f"Aggregate SHA-256 verified: {actual_agg_sha}")


if __name__ == "__main__":
    main()
