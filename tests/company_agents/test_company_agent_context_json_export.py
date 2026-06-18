"""Tests for company agent context JSON export."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_company_agent_context.py"

KNOWN_AGENTS = ["A00", "A10", "A11", "A20", "A21", "A40", "A42"]


def test_json_export_returns_valid_json():
    for agent_id in KNOWN_AGENTS:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id, "--format", "json"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"JSON export failed for {agent_id}: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["agent_id"] == agent_id


def test_json_export_has_required_fields():
    for agent_id in KNOWN_AGENTS:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id, "--format", "json"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        data = json.loads(result.stdout)
        assert "agent_id" in data
        assert "slug" in data
        assert "display_name" in data
        assert "context" in data
        assert "combined_context" in data
        assert "identity" in data["context"]
        assert "soul" in data["context"]
        assert "agent" in data["context"]


def test_json_export_with_metadata():
    for agent_id in ["A00", "A10", "A42"]:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id, "--format", "json", "--include-metadata"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "metadata" in data
        assert data["metadata"]["agent_scope"] == "company_operations"
        assert data["metadata"]["execution_allowed"] is False


def test_json_export_unknown_agent_returns_error():
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--agent-id", "Z99", "--format", "json"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0


def test_markdown_export_still_works():
    for agent_id in KNOWN_AGENTS:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0
        assert "# FILE: identity.md" in result.stdout
        assert "# FILE: soul.md" in result.stdout
        assert "# FILE: agent.md" in result.stdout


def test_markdown_export_with_include_metadata():
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--agent-id", "A00", "--include-metadata"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert "# FILE: metadata.json" in result.stdout
    assert "# FILE: identity.md" in result.stdout


def test_json_export_to_file(tmp_path):
    output_file = tmp_path / "A00_context.json"
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--agent-id", "A00", "--format", "json", "--output", str(output_file)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert data["agent_id"] == "A00"


def test_markdown_export_to_file(tmp_path):
    output_file = tmp_path / "A00_context.md"
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--agent-id", "A00", "--output", str(output_file)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    assert output_file.exists()
    content = output_file.read_text()
    assert "# FILE: identity.md" in content


def test_no_script_imports_llm():
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--agent-id", "A00", "--format", "json"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert "openai" not in result.stderr.lower()
    assert "anthropic" not in result.stderr.lower()
    assert "network" not in result.stderr.lower()
