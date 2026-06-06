#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from src.modules.commercial_prebid_demo.schemas import RunCommercialPreBidDemoRequest
from src.modules.commercial_prebid_demo.service import run_commercial_prebid_demo
from src.shared.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic commercial pre-bid demo.")
    parser.add_argument("--fixture", default="commercial_mvp_demo")
    parser.add_argument("--output-dir", default="tmp/commercial_prebid_demo")
    parser.add_argument("--provider", default="deterministic", choices=["deterministic", "stub", "llm"])
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as session:
        result = run_commercial_prebid_demo(
            session,
            RunCommercialPreBidDemoRequest(
                fixture_name=args.fixture,
                provider=args.provider,
            ),
        )

    markdown_path = output_dir / f"{result.deal_id}_prebid_report.md"
    json_path = output_dir / f"{result.deal_id}_prebid_report.json"
    markdown_path.write_text(result.report_markdown, encoding="utf-8")
    json_path.write_text(json.dumps(result.report_json, ensure_ascii=False, indent=2), encoding="utf-8")

    print(markdown_path)
    print(json_path)


if __name__ == "__main__":
    main()
