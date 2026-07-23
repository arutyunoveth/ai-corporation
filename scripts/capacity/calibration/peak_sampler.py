"""
Utility to sample peak storage scenarios from the calibration aggregate.

Usage:
    python scripts/capacity/calibration/peak_sampler.py \\
        --aggregate samples/capacity/public-r3-calibration.aggregate.json \\
        --output /tmp/peak-scenario.json
"""

import argparse
import json
from pathlib import Path


def load_aggregate(path):
    return json.loads(Path(path).read_text())


def compute_peak_scenario(aggregate, cases, runs_per_case, retention_years):
    agg = aggregate["overall_aggregate"]
    per_case_fs_p95 = agg["filesystem_data_delta_bytes"]["max"]
    total_cases = cases * retention_years
    total_runs = total_cases * runs_per_case

    return {
        "description": "Peak storage scenario for R3 metadata calibration",
        "derived_from": aggregate["measurement_id"],
        "assumptions": {
            "cases_per_year": cases,
            "retention_years": retention_years,
            "runs_per_case": runs_per_case,
        },
        "peak_estimates": {
            "total_cases": total_cases,
            "total_analysis_runs": total_runs,
            "filesystem_storage_bytes": {
                "per_case_p95": per_case_fs_p95,
                "total_ingestion": per_case_fs_p95 * total_cases,
                "total_all_runs": per_case_fs_p95 * total_runs,
            },
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Sample peak storage scenarios")
    parser.add_argument("--aggregate", required=True)
    parser.add_argument("--cases", type=int, default=100000)
    parser.add_argument("--runs-per-case", type=int, default=3)
    parser.add_argument("--retention-years", type=int, default=5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    aggregate = load_aggregate(args.aggregate)
    scenario = compute_peak_scenario(
        aggregate, args.cases, args.runs_per_case, args.retention_years
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scenario, indent=2))
    print(f"Peak scenario written to {output_path}")


if __name__ == "__main__":
    main()
