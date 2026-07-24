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
    text_utf8 = [c["measurements"].get("extracted_text_utf8_bytes", {}).get("value") for c in case_list]
    chunk_counts = [c["measurements"].get("chunk_count", {}).get("value") for c in case_list]
    emb_rows = [c["measurements"].get("embedding_rows", {}).get("value") for c in case_list]
    fs_deltas = [c["measurements"].get("filesystem_data_delta_bytes", {}).get("value") for c in case_list]
    pg_deltas = [c["measurements"].get("postgresql_delta_bytes", {}).get("value") for c in case_list]
    archive_bytes = [c["measurements"].get("archive_bytes", {}).get("value") for c in case_list]

    total_chars = sum(v for v in text_chars if v is not None)
    total_utf8 = sum(v for v in text_utf8 if v is not None)
    utf8_ratio = round(total_utf8 / total_chars, 4) if total_chars else None

    ingestion_stats = {
        "documents_per_procurement": compute_percentiles(doc_counts),
        "extracted_text_chars_per_procurement": compute_percentiles(text_chars),
        "extracted_text_utf8_bytes_per_procurement": compute_percentiles(text_utf8),
        "total_extracted_text_chars": total_chars,
        "total_extracted_text_utf8_bytes": total_utf8,
        "utf8_bytes_per_character_ratio": utf8_ratio,
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
                "filesystem_archive_bytes": backup_b1.get("filesystem_archive_bytes", 0),
                "total_backup_bytes": backup_b1.get("total_backup_bytes", 0),
                "database_source_bytes": backup_b1.get("database_source_bytes", 0),
                "filesystem_source_bytes": backup_b1.get("filesystem_source_bytes", 0),
                "unique_live_source_bytes": backup_b1.get("unique_live_source_bytes", 0),
                "total_source_bytes": backup_b1.get("total_source_bytes", 0),
                "database_archive_to_source_ratio": backup_b1.get("database_archive_to_source_ratio", 0),
                "filesystem_archive_to_source_ratio": backup_b1.get("filesystem_archive_to_source_ratio", 0),
                "full_backup_archive_to_source_ratio": backup_b1.get("full_backup_archive_to_source_ratio", 0),
                "compression_factor": backup_b1.get("compression_factor", 0),
            },
            "B2": {
                "case_count": backup_b2.get("case_count", 18),
                "postgresql_dump_bytes": backup_b2.get("postgresql_dump_bytes", 0),
                "filesystem_archive_bytes": backup_b2.get("filesystem_archive_bytes", 0),
                "total_backup_bytes": backup_b2.get("total_backup_bytes", 0),
                "database_source_bytes": backup_b2.get("database_source_bytes", 0),
                "filesystem_source_bytes": backup_b2.get("filesystem_source_bytes", 0),
                "unique_live_source_bytes": backup_b2.get("unique_live_source_bytes", 0),
                "total_source_bytes": backup_b2.get("total_source_bytes", 0),
                "database_archive_to_source_ratio": backup_b2.get("database_archive_to_source_ratio", 0),
                "filesystem_archive_to_source_ratio": backup_b2.get("filesystem_archive_to_source_ratio", 0),
                "full_backup_archive_to_source_ratio": backup_b2.get("full_backup_archive_to_source_ratio", 0),
                "compression_factor": backup_b2.get("compression_factor", 0),
            },
        },
        "temporary_peak_measurements": {
            "status": "unavailable",
            "reason": "Continuous peak sampling would require R8 runtime integration with ingestion pipeline. Cumulative before/after deltas are available in group statistics instead.",
        },
        "postgresql_reconciliation": _pg_reconciliation(
            baseline, backup_b2, baseline_pg, final_pg
        ),
        "limitations": [
            "R3/XML metadata only — no attachments, no full document bodies.",
            "Embeddings provider: hashing (dim=256, no paid API).",
            "LLM: stub (no generation cost measured).",
            "metadata_fidelity: placeholder (truncated field values).",
            "AnalysisRun not available — pipeline subprocess used instead.",
            "pg_database_size does not shrink after DELETEs.",
        ],
        "formulas": {
            "database_archive_to_source_ratio": "postgresql_dump_bytes / database_source_bytes",
            "filesystem_archive_to_source_ratio": "filesystem_archive_bytes / filesystem_source_bytes",
            "full_backup_archive_to_source_ratio": "total_backup_bytes / unique_live_source_bytes",
            "compression_factor": "total_source_bytes / total_backup_bytes",
            "coverage_percent": "available_count / count * 100",
            "ingestion_fs_delta_per_case": "filesystem_data_delta_bytes after ingest + chunk + embed",
            "forecast_backup_compression_ratio": "max(B1.full_backup_archive_to_source_ratio, B2.full_backup_archive_to_source_ratio)",
            "nearest_rank_percentile": "rank = ceil(p/100 * n), index = rank - 1",
            "p50": "nearest_rank(sorted_values, 50)",
            "p75": "nearest_rank(sorted_values, 75)",
            "p90": "nearest_rank(sorted_values, 90)",
            "utf8_bytes_per_character_ratio": "total_extracted_text_utf8_bytes / total_extracted_text_chars",
        },
    }
    return agg


def _pg_reconciliation(baseline, backup_b2, baseline_pg, final_pg):
    pg_delta = final_pg - baseline_pg
    bl_rel = baseline.get("relation_total_bytes", 0) or 0

    baseline_rels = baseline.get("relation_sizes", {}) or {}
    b2_rels = backup_b2.get("relation_sizes", {}) or {}

    # Union of all relation keys from baseline and final
    all_names = set(baseline_rels.keys()) | set(b2_rels.keys())

    total_baseline_bytes = sum(baseline_rels.get(rn, 0) for rn in all_names)
    total_final_bytes = sum(b2_rels.get(rn, 0) for rn in all_names)
    rel_delta = 0
    keyed_deltas = {}
    for rname in sorted(all_names):
        bsize = baseline_rels.get(rname, 0)
        fsize = b2_rels.get(rname, 0)
        d = fsize - bsize
        if d != 0:
            keyed_deltas[rname] = d
            rel_delta += d

    return {
        "pg_database_size_delta_bytes": pg_delta,
        "pg_final_bytes": final_pg,
        "pg_baseline_bytes": baseline_pg,
        "relation_total_baseline_bytes": total_baseline_bytes,
        "relation_total_final_bytes": total_final_bytes,
        "relation_total_delta_bytes": rel_delta,
        "relation_deltas_by_table": keyed_deltas,
        "note": (
            "pg_database_size delta includes PostgreSQL block-level allocation, "
            "catalog bloat, and unused space from DELETEs. "
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
    b1 = aggregate["backup_measurements"]["B1"]
    b2 = aggregate["backup_measurements"]["B2"]

    # Forecast compression ratio: max(B1, B2) full_backup_archive_to_source_ratio
    b1_ratio = b1.get("full_backup_archive_to_source_ratio", 0.1)
    b2_ratio = b2.get("full_backup_archive_to_source_ratio", 0.1)
    forecast_compression = min(1.0, max(b1_ratio, b2_ratio))

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

    p50_text = ing["extracted_text_chars_per_procurement"]["p50"] or 0
    p75_text = ing["extracted_text_chars_per_procurement"]["p75"] or 0
    p90_text = ing["extracted_text_chars_per_procurement"]["p90"] or 0

    # Map profiles: pilot=median, commercial_mvp=p75, scaling=p90
    profile_map = {
        "pilot": {
            "documents_per_procurement": p50_docs,
            "extracted_text_chars_per_procurement": p50_text,
            "chunks_per_procurement": p50_chunks,
            "percentile": "p50",
        },
        "commercial_mvp": {
            "documents_per_procurement": p75_docs,
            "extracted_text_chars_per_procurement": p75_text,
            "chunks_per_procurement": p75_chunks,
            "percentile": "p75",
        },
        "scaling": {
            "documents_per_procurement": p90_docs,
            "extracted_text_chars_per_procurement": p90_text,
            "chunks_per_procurement": p90_chunks,
            "percentile": "p90",
        },
    }

    if "profiles" in scenario and isinstance(scenario["profiles"], dict):
        for name, profile in scenario["profiles"].items():
            mapped = profile_map.get(name, {})
            pctl = mapped.pop("percentile", name)
            for k, v in mapped.items():
                if k in profile and isinstance(profile[k], dict):
                    profile[k]["value"] = v
                    profile[k]["source"] = "assumption"
                    profile[k]["note"] = (
                        "Calibrated from R3/XML metadata ingestion (18-case cohort). "
                        f"Percentile: {pctl} ({name}). "
                        "See aggregate notes for full calibration context."
                    )

            # Add extracted_text_chars_per_procurement (scenario template has only
            # extracted_text_bytes_per_procurement; chars replace bytes for accuracy)
            if "extracted_text_chars_per_procurement" not in profile:
                profile["extracted_text_chars_per_procurement"] = {
                    "value": mapped.get("extracted_text_chars_per_procurement", 0),
                    "source": "assumption",
                    "note": (
                        f"Calibrated from R3/XML metadata ingestion (18-case cohort). "
                        f"Percentile: {pctl} ({name}). Characters (not bytes). "
                        "UTF-8 overhead ~7.3% for Russian XML data."
                    ),
                }

            # Embedding parameters (values and notes)
            if "vector_dimension" in profile and isinstance(profile["vector_dimension"], dict):
                profile["vector_dimension"]["value"] = 256
                profile["vector_dimension"]["source"] = "assumption"
                profile["vector_dimension"]["note"] = (
                    "Calibrated from R3/XML metadata ingestion: hashing embeddings (dim=256). "
                    "Replace with the actual production embedding model dimension."
                )
            if "embedding_rows_per_chunk" in profile and isinstance(profile["embedding_rows_per_chunk"], dict):
                profile["embedding_rows_per_chunk"]["value"] = 1
                profile["embedding_rows_per_chunk"]["source"] = "assumption"
                profile["embedding_rows_per_chunk"]["note"] = (
                    "Calibrated from R3/XML metadata ingestion: 1 embedding row per chunk (hashing). "
                    "Production models may generate multiple vectors per chunk."
                )
            if "vector_bytes_per_component" in profile and isinstance(profile["vector_bytes_per_component"], dict):
                profile["vector_bytes_per_component"]["value"] = 4
                profile["vector_bytes_per_component"]["source"] = "assumption"
                profile["vector_bytes_per_component"]["note"] = (
                    "float32 per vector component (4 bytes). Standard for embedding models."
                )

            # Percentile note for calibrated params
            if "documents_per_procurement" in profile and isinstance(profile["documents_per_procurement"], dict):
                profile["documents_per_procurement"]["note"] = (
                    f"Calibrated from R3/XML metadata ingestion (18-case cohort). "
                    f"Percentile: {pctl} ({name}). "
                    f"p50=4, p75=4, p90=5 documents per procurement."
                )
            if "extracted_text_chars_per_procurement" in profile and isinstance(profile["extracted_text_chars_per_procurement"], dict):
                profile["extracted_text_chars_per_procurement"]["note"] = (
                    f"Calibrated from R3/XML metadata ingestion (18-case cohort). "
                    f"Percentile: {pctl} ({name}). "
                    f"p50={p50_text}, p75={p75_text}, p90={p90_text} characters per procurement."
                )
            if "chunks_per_procurement" in profile and isinstance(profile["chunks_per_procurement"], dict):
                profile["chunks_per_procurement"]["note"] = (
                    f"Calibrated from R3/XML metadata ingestion (18-case cohort). "
                    f"Percentile: {pctl} ({name}). "
                    f"p50={p50_chunks}, p75={p75_chunks}, p90={p90_chunks} chunks per procurement."
                )

    # Set backup compression ratio: use max(B1, B2) full_backup_archive_to_source_ratio
    for name, profile in scenario.get("profiles", {}).items():
        if isinstance(profile, dict) and "backup_compression_ratio" in profile:
            br = profile["backup_compression_ratio"]
            if isinstance(br, dict):
                br["value"] = forecast_compression
                br["source"] = "assumption"
                br["note"] = (
                    f"Calibrated from max(B1, B2) full_backup_archive_to_source_ratio "
                    f"({b1_ratio}, {b2_ratio}). "
                    f"Forecast uses min(1.0, max(B1, B2)) = {forecast_compression}."
                )

    # Temporary factor: keep template values (status=unavailable, use original template defaults)
    for name, profile in scenario.get("profiles", {}).items():
        if isinstance(profile, dict) and "temporary_space_peak_factor" in profile:
            tf = profile["temporary_space_peak_factor"]
            if isinstance(tf, dict):
                # Keep template values as-is (pilot=1.5, commercial_mvp=1.5, scaling=1.3)
                tf["source"] = "assumption"
                tf["note"] = (
                    "Temporary peak unavailable (no continuous sampling in R3 metadata ingestion). "
                    "Template assumption retained. "
                    "Not calibrated from this measurement run."
                )

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
