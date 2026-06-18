#!/usr/bin/env python3
"""Export company agent context from local assets.

Usage:
    python -m scripts.export_company_agent_context --agent-id A00
    python -m scripts.export_company_agent_context --agent-id A10

This script only reads local files. It does not call any LLM,
make network requests, or send data to external APIs.
"""

import argparse
import sys
from pathlib import Path

AGENT_BASE_DIR = Path(__file__).resolve().parent.parent / "docs" / "agents" / "company"
REQUIRED_FILES = ["identity.md", "soul.md", "agent.md"]

KNOWN_AGENTS = {
    "A00": "A00_chief_of_staff",
    "A10": "A10_tender_operator",
    "A11": "A11_rfq_supplier_analyst",
    "A20": "A20_finance_unit_economics",
    "A21": "A21_legal_contract_risk",
    "A40": "A40_cto_system_architect",
    "A42": "A42_qa_release",
}


def export_agent_context(agent_id: str) -> str:
    if agent_id not in KNOWN_AGENTS:
        known = ", ".join(sorted(KNOWN_AGENTS.keys()))
        raise SystemExit(f"Error: agent '{agent_id}' not found. Known agents: {known}")

    agent_dir = AGENT_BASE_DIR / KNOWN_AGENTS[agent_id]
    if not agent_dir.is_dir():
        raise SystemExit(f"Error: agent directory not found: {agent_dir}")

    parts: list[str] = []
    for filename in REQUIRED_FILES:
        filepath = agent_dir / filename
        if not filepath.is_file():
            raise SystemExit(f"Error: missing required file '{filename}' for agent '{agent_id}' at {filepath}")
        content = filepath.read_text(encoding="utf-8")
        parts.append(f"# FILE: {filename}\n\n{content}")

    return "\n\n---\n\n".join(parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Arvectum company agent context from local assets."
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        help="Agent ID to export (e.g., A00, A10, A11, A20, A21, A40, A42)",
    )
    args = parser.parse_args()

    output = export_agent_context(args.agent_id)
    print(output)


if __name__ == "__main__":
    main()
