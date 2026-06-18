"""Tests for Hermes manual context boundary enforcement."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SCRIPT = REPO_ROOT / "scripts" / "export_hermes_company_manifest.py"
CONTEXT_SCRIPT = REPO_ROOT / "scripts" / "export_company_agent_context.py"
ROUTE_SCRIPT = REPO_ROOT / "scripts" / "export_company_workflow_route.py"


def test_no_script_performs_network_calls():
    scripts = [MANIFEST_SCRIPT, CONTEXT_SCRIPT, ROUTE_SCRIPT]
    for script in scripts:
        result = subprocess.run(
            [sys.executable, str(script), "--help"] if script == ROUTE_SCRIPT else [sys.executable, str(script), "--agent-id", "A00"] if script == CONTEXT_SCRIPT else [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        stderr_lower = result.stderr.lower()
        assert "http" not in stderr_lower or "https" not in stderr_lower, f"{script.name} may make network calls"
        assert "connection" not in stderr_lower, f"{script.name} may make network calls"


def test_no_script_imports_llm_clients():
    scripts = [CONTEXT_SCRIPT, ROUTE_SCRIPT]
    for script in scripts:
        result = subprocess.run(
            [sys.executable, str(script), "--agent-id", "A00"] if script == CONTEXT_SCRIPT else [sys.executable, str(script), "--route-id", "company_tender_bid_no_bid"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        stderr_lower = result.stderr.lower()
        assert "openai" not in stderr_lower
        assert "anthropic" not in stderr_lower
        assert "ollama" not in stderr_lower


def test_manifest_enforces_no_execution():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    manifest = json.loads(result.stdout)
    assert manifest["execution_allowed"] is False
    assert manifest["autonomous_execution_allowed"] is False
    assert manifest["cloud_dispatch_allowed"] is False
    assert manifest["runtime_mode"] == "manual_context_only"


def test_all_agents_have_execution_allowed_false():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    manifest = json.loads(result.stdout)
    for agent in manifest["agents"]:
        # Agents don't have execution_allowed in manifest, but runtime_mode should be safe
        assert agent["runtime_mode"] in ("manual_context_only", "metadata_only"), (
            f"Agent {agent['agent_id']} has unexpected runtime_mode: {agent['runtime_mode']}"
        )


def test_all_routes_have_runtime_execution_not_allowed():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    manifest = json.loads(result.stdout)
    for route in manifest["routes"]:
        assert route["runtime_execution_allowed"] is False, (
            f"Route {route['route_id']} has runtime_execution_allowed=True"
        )


def test_json_export_has_execution_allowed_false():
    result = subprocess.run(
        [sys.executable, str(CONTEXT_SCRIPT), "--agent-id", "A00", "--format", "json", "--include-metadata"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    data = json.loads(result.stdout)
    assert data["metadata"]["execution_allowed"] is False


def test_active_agents_are_metadata_only():
    from src.modules.agent_registry.company_agents import get_active_company_agents

    active = get_active_company_agents()
    for agent in active:
        assert agent.runtime_mode.value in ("manual_context_only", "metadata_only"), (
            f"Active agent {agent.agent_key} has unexpected runtime_mode: {agent.runtime_mode}"
        )
