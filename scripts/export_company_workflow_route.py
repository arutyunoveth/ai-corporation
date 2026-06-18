#!/usr/bin/env python3
"""Export company workflow route metadata for Hermes.

Usage:
    python -m scripts.export_company_workflow_route --route-id company_tender_bid_no_bid

This script only reads local metadata. It does not call any LLM,
make network requests, or send data to external APIs.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.modules.workflow_runs.company_workflow_routes import (
    get_company_workflow_route,
    list_company_workflow_routes,
)

ROUTE_STEPS = {
    "company_tender_bid_no_bid": [
        {"step": 1, "agent_id": "A10", "action": "Load Tender Operator context"},
        {"step": 2, "agent_id": "A11", "action": "Load RFQ & Supplier Analyst context"},
        {"step": 3, "agent_id": "A20", "action": "Load Finance & Unit Economics context"},
        {"step": 4, "agent_id": "A21", "action": "Load Legal & Contract Risk context"},
        {"step": 5, "agent_id": "A42", "action": "Load QA & Release context"},
        {"step": 6, "agent_id": "A10", "action": "Prepare CEO Decision Memo"},
    ],
    "company_architecture_review": [
        {"step": 1, "agent_id": "A40", "action": "Load CTO / System Architect context"},
        {"step": 2, "agent_id": "A42", "action": "Load QA & Release context"},
        {"step": 3, "agent_id": "A40", "action": "Prepare Architecture Decision Record"},
    ],
    "company_release_readiness": [
        {"step": 1, "agent_id": "A42", "action": "Load QA & Release context"},
        {"step": 2, "agent_id": "A40", "action": "Load CTO / System Architect context"},
        {"step": 3, "agent_id": "A42", "action": "Prepare QA Readiness Memo"},
    ],
    "company_marketing_asset_review": [
        {"step": 1, "agent_id": "A51", "action": "Load Marketing & Brand context"},
        {"step": 2, "agent_id": "A52", "action": "Load Proposal / Commercial Docs context"},
        {"step": 3, "agent_id": "A51", "action": "Prepare Marketing Asset Approval Memo"},
    ],
    "company_sales_lead_qualification": [
        {"step": 1, "agent_id": "A50", "action": "Load Sales Development context"},
        {"step": 2, "agent_id": "A20", "action": "Load Finance & Unit Economics context"},
        {"step": 3, "agent_id": "A21", "action": "Load Legal & Contract Risk context"},
        {"step": 4, "agent_id": "A50", "action": "Prepare Lead Qualification Memo"},
    ],
}


def build_route_export(route_id: str) -> dict:
    route = get_company_workflow_route(route_id)
    steps = ROUTE_STEPS.get(route_id, [
        {"step": i + 1, "agent_id": route.owner, "action": f"Load {route.owner} context"}
        for i in range(len(route.supporting_agents) + 1)
    ])

    return {
        "route_id": route.route_id,
        "execution_mode": route.execution_mode,
        "runtime_execution_allowed": route.runtime_execution_allowed,
        "owner": route.owner,
        "supporting_agents": route.supporting_agents,
        "final_artifact": route.final_artifact,
        "recommended_steps": steps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Arvectum company workflow route metadata."
    )
    parser.add_argument(
        "--route-id",
        required=True,
        help="Route ID to export (e.g., company_tender_bid_no_bid)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path. If not specified, prints to stdout.",
    )
    args = parser.parse_args()

    try:
        route_export = build_route_export(args.route_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    output = json.dumps(route_export, indent=2, ensure_ascii=False)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Route export written to {output_path}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
