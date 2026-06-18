#!/usr/bin/env python3
"""Export Hermes-compatible company agent manifest.

Usage:
    python -m scripts.export_hermes_company_manifest
    python -m scripts.export_hermes_company_manifest --output tmp/hermes_company_manifest.json

This script only reads local files and metadata. It does not call any LLM,
make network requests, or send data to external APIs.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.modules.agent_registry.company_agents import (
    COMPANY_AGENTS,
    INACTIVE_AGENTS,
    get_active_company_agents,
)
from src.modules.workflow_runs.company_workflow_routes import list_company_workflow_routes


def _agent_to_manifest_entry(agent) -> dict:
    agent_dir_name = {
        "A00": "A00_chief_of_staff",
        "A10": "A10_tender_operator",
        "A11": "A11_rfq_supplier_analyst",
        "A20": "A20_finance_unit_economics",
        "A21": "A21_legal_contract_risk",
        "A40": "A40_cto_system_architect",
        "A42": "A42_qa_release",
    }.get(agent.agent_key, f"{agent.agent_key}_{agent.agent_label.lower().replace(' ', '_').replace('/', '_')}")

    context_base = f"docs/agents/company/{agent_dir_name}"

    return {
        "agent_id": agent.agent_key,
        "slug": agent.agent_label.lower().replace(" & ", "_").replace(" / ", "_").replace(" ", "_"),
        "display_name": agent.agent_label,
        "agent_scope": agent.agent_scope.value if agent.agent_scope else None,
        "agent_kind": agent.agent_kind.value if agent.agent_kind else None,
        "activation_state": agent.activation_state.value,
        "data_policy": agent.data_policy.value if agent.data_policy else None,
        "runtime_mode": agent.runtime_mode.value if agent.runtime_mode else None,
        "model_tier": agent.model_tier.value if agent.model_tier else None,
        "context_files": {
            "identity": f"{context_base}/identity.md",
            "soul": f"{context_base}/soul.md",
            "agent": f"{context_base}/agent.md",
        },
        "context_export_command": f"python -m scripts.export_company_agent_context --agent-id {agent.agent_key}",
    }


def _route_to_manifest_entry(route) -> dict:
    return {
        "route_id": route.route_id,
        "execution_mode": route.execution_mode,
        "runtime_execution_allowed": route.runtime_execution_allowed,
        "owner": route.owner,
        "supporting_agents": route.supporting_agents,
        "final_artifact": route.final_artifact,
    }


def build_manifest() -> dict:
    active_agents = get_active_company_agents()
    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    routes = list_company_workflow_routes()

    return {
        "company": "Arvectum",
        "system": "Company Operations Agents",
        "scope": "company_operations",
        "runtime_mode": "manual_context_only",
        "execution_allowed": False,
        "autonomous_execution_allowed": False,
        "cloud_dispatch_allowed": False,
        "default_execution_policy": {
            "mode": "sequential",
            "max_parallel_local_agents": 1,
            "local_first": True,
        },
        "agents": [_agent_to_manifest_entry(a) for a in all_agents],
        "active_agent_count": len(active_agents),
        "total_agent_count": len(all_agents),
        "routes": [_route_to_manifest_entry(r) for r in routes],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Arvectum Hermes-compatible company agent manifest."
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path. If not specified, prints to stdout.",
    )
    args = parser.parse_args()

    manifest = build_manifest()
    output = json.dumps(manifest, indent=2, ensure_ascii=False)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Manifest written to {output_path}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
