"""
Usage:
    python scripts/capacity/calibration/calibrate_cohort.py \\
        --manifest /path/to/manifest.json \\
        --runtime /tmp/arvectum-arv009-b22 \\
        --output /path/to/aggregate.json
"""

import argparse
import json
import sys
from pathlib import Path


def load_manifest(path):
    with open(path) as f:
        return json.load(f)


def load_cohort_measurements(runtime_path):
    runtime = Path(runtime_path)
    cohort = json.loads((runtime / "measurements/cohort.json").read_text())
    baseline = json.loads((runtime / "measurements/baseline.json").read_text())
    backup = json.loads((runtime / "measurements/backup-obs.json").read_text())
    return cohort, baseline, backup


def compute_percentile(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        return {}
    return {
        "min": s[0],
        "p25": s[n // 4],
        "p50": s[n // 2],
        "p75": s[3 * n // 4],
        "max": s[-1],
        "count": n,
        "sum": sum(s),
        "mean": round(sum(s) / n, 1),
    }


def build_aggregate(cohort, baseline, backup):
    cases = list(cohort["cases"].values())

    groups = {}
    for c in cases:
        groups.setdefault(c["group"], []).append(c)

    group_stats = {}
    for g, lst in groups.items():
        m = {}
        for k in ["xml_document_count", "extracted_text_chars", "chunk_count",
                   "embedding_rows", "archive_bytes", "postgresql_delta_bytes",
                   "filesystem_data_delta_bytes"]:
            vals = [c["measurements"].get(k, {}).get("value", 0) for c in lst]
            m[k] = compute_percentile(vals)
        group_stats[g] = m

    overall = {}
    for k in ["xml_document_count", "extracted_text_chars", "chunk_count",
              "embedding_rows", "archive_bytes", "postgresql_delta_bytes",
              "filesystem_data_delta_bytes"]:
        vals = [c["measurements"].get(k, {}).get("value") for c in cases]
        vals = [v for v in vals if v is not None]
        if vals:
            overall[k] = compute_percentile(vals)

    pg_growth = backup["postgresql_database_bytes"] - baseline.get("postgresql_database_bytes", 0)
    fs_growth = backup["unique_live_source_bytes"] - baseline.get("filesystem_data_bytes", 0)
    metadata_overhead = round(pg_growth / max(fs_growth, 1), 2) if fs_growth > 0 else 1.0

    aggregate = {
        "measurement_id": "ARV-009-B2-R3-METADATA-CALIBRATION",
        "description": "Calibration aggregate for R3 metadata storage",
        "cohort": {
            "version": "r3-v1",
            "total_cases": cohort["manifest"]["total_cases"],
            "tertile_groups": cohort["manifest"]["tertile_groups"],
            "scenario": "full_r3_metadata_calibration",
        },
        "baseline": {
            "postgresql_database_bytes_baseline": baseline.get("postgresql_database_bytes", 0),
            "filesystem_data_bytes_baseline": baseline.get("filesystem_data_bytes", 0),
            "filesystem_index_bytes_baseline": baseline.get("filesystem_index_bytes", 0),
            "postgresql_dump_bytes_baseline": baseline.get("postgresql_dump_bytes", 0),
        },
        "final_state": {
            "postgresql_database_bytes": backup["postgresql_database_bytes"],
            "filesystem_live_bytes": backup["filesystem_live_bytes"],
            "total_backup_bytes": backup["total_backup_bytes"],
            "unique_live_source_bytes": backup["unique_live_source_bytes"],
            "document_count": backup["document_count"],
            "analysis_run_count": backup.get("analysis_run_count", 0),
        },
        "overall_aggregate": overall,
        "group_aggregates": group_stats,
        "compression_ratios": {
            "observed_backup_ratio": backup["observed_compression_ratio"],
            "forecast_compression_ratio": backup["forecast_compression_ratio"],
            "metadata_overhead_ratio": metadata_overhead,
        },
        "notes": [
            "PG dump compression: observed {:.2f}x on this sample.".format(
                backup["observed_compression_ratio"]
            ),
            "Forecast compression ratio set to 1.0 for conservative capacity planning.",
            "Metadata overhead ratio: PG growth / FS growth after baseline subtraction.",
        ],
    }
    return aggregate


def main():
    parser = argparse.ArgumentParser(description="Calibrate R3 metadata cohort")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    cohort, baseline, backup = load_cohort_measurements(args.runtime)
    aggregate = build_aggregate(cohort, baseline, backup)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(aggregate, indent=2))
    print(f"Aggregate written to {output_path}")


if __name__ == "__main__":
    main()
