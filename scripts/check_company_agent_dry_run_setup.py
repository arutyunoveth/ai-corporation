#!/usr/bin/env python3
"""Validate that Dry Run 0 setup is complete and correct.

Usage:
    python -m scripts.check_company_agent_dry_run_setup

Checks:
1. Dry Run 0 directory exists.
2. CEO instruction exists.
3. Run manifest template exists.
4. Required templates exist.
5. Required agent contexts can be exported.
6. Route company_pilot_readiness_review can be exported.
7. Manifest can be exported.
8. No runtime execution flag is true.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

REQUIRED_AGENTS = ["A00", "A10", "A20", "A21", "A42"]

REQUIRED_TEMPLATES = [
    "docs/agents/company/templates/A00_routing_memo.md",
    "docs/agents/company/templates/A10_tender_operations_readiness.md",
    "docs/agents/company/templates/A20_finance_readiness.md",
    "docs/agents/company/templates/A21_legal_risk_readiness.md",
    "docs/agents/company/templates/A42_qa_release_readiness.md",
    "docs/agents/company/templates/A00_final_synthesis.md",
    "docs/agents/company/templates/ceo_decision_memo.md",
]

DRY_RUN_DIR = REPO_ROOT / "company_agent_runs" / "dry_run_0"
CEO_INSTRUCTION = DRY_RUN_DIR / "input" / "ceo_instruction.md"
RUN_MANIFEST_TEMPLATE = DRY_RUN_DIR / "run_manifest.template.json"
DRY_RUN_README = DRY_RUN_DIR / "README.md"


def _check(condition: bool, label: str, errors: list[str]) -> None:
    if not condition:
        errors.append(f"FAIL: {label}")
    else:
        print(f"  PASS: {label}")


def main() -> int:
    errors: list[str] = []

    print("Checking Dry Run 0 setup...")

    # 1. Directory
    _check(DRY_RUN_DIR.is_dir(), "Dry Run 0 directory exists", errors)

    # 2. CEO instruction
    _check(CEO_INSTRUCTION.is_file(), "CEO instruction exists", errors)

    # 3. Run manifest template
    _check(RUN_MANIFEST_TEMPLATE.is_file(), "Run manifest template exists", errors)

    # 4. README
    _check(DRY_RUN_README.is_file(), "Dry Run 0 README exists", errors)

    # 5. Templates
    for tpl in REQUIRED_TEMPLATES:
        tpl_path = REPO_ROOT / tpl
        _check(tpl_path.is_file(), f"Template: {tpl}", errors)

    # 6. Agent contexts can be exported
    try:
        from scripts.export_company_agent_context import load_agent_context

        for agent_id in REQUIRED_AGENTS:
            try:
                ctx = load_agent_context(agent_id)
                _check(
                    "identity" in ctx and "soul" in ctx and "agent" in ctx,
                    f"Agent {agent_id} context exportable",
                    errors,
                )
            except Exception as exc:
                errors.append(f"FAIL: Agent {agent_id} context export error: {exc}")
    except ImportError as exc:
        errors.append(f"FAIL: Cannot import export_company_agent_context: {exc}")

    # 7. Route exists and is safe
    try:
        from src.modules.workflow_runs.company_workflow_routes import (
            get_company_workflow_route,
        )

        route = get_company_workflow_route("company_pilot_readiness_review")
        _check(route.runtime_execution_allowed is False, "Route runtime_execution_allowed = false", errors)
        _check(route.owner == "A00", "Route owner = A00", errors)
    except Exception as exc:
        errors.append(f"FAIL: Route check error: {exc}")

    # 8. Manifest can be exported
    try:
        from scripts.export_hermes_company_manifest import build_manifest

        manifest = build_manifest()
        _check(
            manifest.get("execution_allowed") is False,
            "Manifest execution_allowed = false",
            errors,
        )
        _check(
            manifest.get("autonomous_execution_allowed") is False,
            "Manifest autonomous_execution_allowed = false",
            errors,
        )
        _check(
            manifest.get("cloud_dispatch_allowed") is False,
            "Manifest cloud_dispatch_allowed = false",
            errors,
        )
    except Exception as exc:
        errors.append(f"FAIL: Manifest export error: {exc}")

    # Summary
    print()
    if errors:
        for e in errors:
            print(e)
        print(f"\nCompany Agent Dry Run 0 setup: FAIL ({len(errors)} errors)")
        return 1

    print("Company Agent Dry Run 0 setup: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
