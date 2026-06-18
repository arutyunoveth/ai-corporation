"""Tests for Hermes company manifest export."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SCRIPT = REPO_ROOT / "scripts" / "export_hermes_company_manifest.py"


def test_manifest_exports_valid_json():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, f"Manifest export failed: {result.stderr}"
    manifest = json.loads(result.stdout)
    assert isinstance(manifest, dict)


def test_manifest_contains_company():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    manifest = json.loads(result.stdout)
    assert manifest["company"] == "Arvectum"
    assert manifest["scope"] == "company_operations"


def test_manifest_contains_all_company_agents():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    manifest = json.loads(result.stdout)
    assert manifest["total_agent_count"] == 21
    assert len(manifest["agents"]) == 21


def test_manifest_contains_seven_active_agents():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    manifest = json.loads(result.stdout)
    assert manifest["active_agent_count"] == 7


def test_manifest_execution_allowed_is_false():
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


def test_manifest_has_default_execution_policy():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    manifest = json.loads(result.stdout)
    policy = manifest["default_execution_policy"]
    assert policy["mode"] == "sequential"
    assert policy["max_parallel_local_agents"] == 1
    assert policy["local_first"] is True


def test_manifest_has_routes():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    manifest = json.loads(result.stdout)
    assert len(manifest["routes"]) >= 5
    route_ids = {r["route_id"] for r in manifest["routes"]}
    assert "company_tender_bid_no_bid" in route_ids


def test_manifest_agents_have_required_fields():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    manifest = json.loads(result.stdout)
    for agent in manifest["agents"]:
        assert "agent_id" in agent
        assert "display_name" in agent
        assert "agent_scope" in agent
        assert "runtime_mode" in agent
        assert "context_files" in agent
        assert "context_export_command" in agent
        assert agent["agent_scope"] == "company_operations"


def test_manifest_output_to_file(tmp_path):
    output_file = tmp_path / "test_manifest.json"
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT), "--output", str(output_file)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert output_file.exists()
    manifest = json.loads(output_file.read_text())
    assert manifest["company"] == "Arvectum"


def test_manifest_does_not_import_llm():
    result = subprocess.run(
        [sys.executable, str(MANIFEST_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert "openai" not in result.stderr.lower()
    assert "anthropic" not in result.stderr.lower()
    assert "llm" not in result.stderr.lower()
