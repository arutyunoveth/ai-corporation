#!/usr/bin/env python3
"""Export company agent context from local assets.

Usage:
    python -m scripts.export_company_agent_context --agent-id A00
    python -m scripts.export_company_agent_context --agent-id A00 --format markdown
    python -m scripts.export_company_agent_context --agent-id A00 --format json
    python -m scripts.export_company_agent_context --agent-id A00 --output tmp/A00_context.md
    python -m scripts.export_company_agent_context --agent-id A00 --include-metadata

This script only reads local files. It does not call any LLM,
make network requests, or send data to external APIs.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.modules.agent_registry.company_agents import COMPANY_AGENTS, INACTIVE_AGENTS

AGENT_BASE_DIR = REPO_ROOT / "docs" / "agents" / "company"
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

ALL_AGENTS = {a.agent_key: a for a in COMPANY_AGENTS + INACTIVE_AGENTS}


def load_agent_context(agent_id: str) -> dict:
    """Load agent context files as a dict. Raises SystemExit on error."""
    if agent_id not in KNOWN_AGENTS:
        known = ", ".join(sorted(KNOWN_AGENTS.keys()))
        raise SystemExit(f"Error: agent '{agent_id}' not found. Known agents: {known}")

    agent_dir = AGENT_BASE_DIR / KNOWN_AGENTS[agent_id]
    if not agent_dir.is_dir():
        raise SystemExit(f"Error: agent directory not found: {agent_dir}")

    context_files = {}
    for filename in REQUIRED_FILES:
        filepath = agent_dir / filename
        if not filepath.is_file():
            raise SystemExit(f"Error: missing required file '{filename}' for agent '{agent_id}' at {filepath}")
        context_files[filename.replace(".md", "")] = filepath.read_text(encoding="utf-8")

    return context_files


def _read_agent_file(agent_id: str, filename: str) -> str:
    agent_dir = AGENT_BASE_DIR / KNOWN_AGENTS[agent_id]
    filepath = agent_dir / filename
    if not filepath.is_file():
        raise SystemExit(f"Error: missing required file '{filename}' for agent '{agent_id}' at {filepath}")
    return filepath.read_text(encoding="utf-8")


def export_agent_context_markdown(agent_id: str, include_metadata: bool = False) -> str:
    if agent_id not in KNOWN_AGENTS:
        known = ", ".join(sorted(KNOWN_AGENTS.keys()))
        raise SystemExit(f"Error: agent '{agent_id}' not found. Known agents: {known}")

    agent_dir = AGENT_BASE_DIR / KNOWN_AGENTS[agent_id]
    if not agent_dir.is_dir():
        raise SystemExit(f"Error: agent directory not found: {agent_dir}")

    parts: list[str] = []

    if include_metadata and agent_id in ALL_AGENTS:
        agent = ALL_AGENTS[agent_id]
        metadata_block = f"""# FILE: metadata.json

```json
{json.dumps({
    "agent_id": agent.agent_key,
    "display_name": agent.agent_label,
    "agent_scope": agent.agent_scope.value if agent.agent_scope else None,
    "agent_kind": agent.agent_kind.value if agent.agent_kind else None,
    "activation_state": agent.activation_state.value,
    "data_policy": agent.data_policy.value if agent.data_policy else None,
    "runtime_mode": agent.runtime_mode.value if agent.runtime_mode else None,
    "model_tier": agent.model_tier.value if agent.model_tier else None,
    "execution_allowed": False,
}, indent=2)}
```"""
        parts.append(metadata_block)

    for filename in REQUIRED_FILES:
        content = _read_agent_file(agent_id, filename)
        parts.append(f"# FILE: {filename}\n\n{content}")

    return "\n\n---\n\n".join(parts) + "\n"


def export_agent_context_json(agent_id: str, include_metadata: bool = False) -> str:
    if agent_id not in KNOWN_AGENTS:
        known = ", ".join(sorted(KNOWN_AGENTS.keys()))
        raise SystemExit(f"Error: agent '{agent_id}' not found. Known agents: {known}")

    agent_dir = AGENT_BASE_DIR / KNOWN_AGENTS[agent_id]
    if not agent_dir.is_dir():
        raise SystemExit(f"Error: agent directory not found: {agent_dir}")

    context_files = {}
    for filename in REQUIRED_FILES:
        context_files[filename.replace(".md", "")] = _read_agent_file(agent_id, filename)

    combined_parts = []
    for filename in REQUIRED_FILES:
        content = context_files[filename.replace(".md", "")]
        combined_parts.append(f"# FILE: {filename}\n\n{content}")
    combined_context = "\n\n---\n\n".join(combined_parts) + "\n"

    result = {
        "agent_id": agent_id,
        "slug": KNOWN_AGENTS[agent_id],
        "display_name": ALL_AGENTS[agent_id].agent_label if agent_id in ALL_AGENTS else KNOWN_AGENTS[agent_id],
        "context": context_files,
        "combined_context": combined_context,
    }

    if include_metadata and agent_id in ALL_AGENTS:
        agent = ALL_AGENTS[agent_id]
        result["metadata"] = {
            "agent_scope": agent.agent_scope.value if agent.agent_scope else None,
            "agent_kind": agent.agent_kind.value if agent.agent_kind else None,
            "activation_state": agent.activation_state.value,
            "data_policy": agent.data_policy.value if agent.data_policy else None,
            "runtime_mode": agent.runtime_mode.value if agent.runtime_mode else None,
            "model_tier": agent.model_tier.value if agent.model_tier else None,
            "execution_allowed": False,
        }

    return json.dumps(result, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Arvectum company agent context from local assets."
    )
    parser.add_argument(
        "--agent-id",
        required=True,
        help="Agent ID to export (e.g., A00, A10, A11, A20, A21, A40, A42)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path. If not specified, prints to stdout.",
    )
    parser.add_argument(
        "--include-metadata",
        action="store_true",
        help="Include agent metadata in the output",
    )
    args = parser.parse_args()

    if args.format == "json":
        output = export_agent_context_json(args.agent_id, include_metadata=args.include_metadata)
    else:
        output = export_agent_context_markdown(args.agent_id, include_metadata=args.include_metadata)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Context written to {output_path}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
