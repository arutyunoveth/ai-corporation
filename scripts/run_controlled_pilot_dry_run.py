#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.modules.controlled_pilot_dry_run.service import run_controlled_pilot_dry_run
from src.shared.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the controlled commercial pilot dry run.")
    parser.add_argument(
        "--fixtures",
        nargs="+",
        default=[
            "controlled_pilot_simple_relevant",
            "controlled_pilot_risky_contract",
            "controlled_pilot_no_go_review",
            "controlled_pilot_tkp_economics",
        ],
    )
    parser.add_argument("--provider", default="stub", choices=["deterministic", "stub", "llm"])
    parser.add_argument("--output-dir", default="tmp/controlled_pilot_dry_run")
    parser.add_argument("--operator-ref", default="pilot.operator")
    args = parser.parse_args()

    summary = run_controlled_pilot_dry_run(
        SessionLocal,
        fixture_names=args.fixtures,
        output_dir=args.output_dir,
        provider=args.provider,
        operator_ref=args.operator_ref,
    )
    print(args.output_dir)
    print(f"completed={summary.completed_scenarios} blocked={summary.blocked_scenarios}")


if __name__ == "__main__":
    main()
