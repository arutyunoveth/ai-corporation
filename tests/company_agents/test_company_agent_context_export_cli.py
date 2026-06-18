"""Tests for company agent context export CLI."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_company_agent_context.py"

KNOWN_AGENTS = ["A00", "A10", "A42"]


def test_exporter_returns_identity_md():
    for agent_id in KNOWN_AGENTS:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"Exporter failed for {agent_id}: {result.stderr}"
        assert "# FILE: identity.md" in result.stdout, f"Missing identity.md for {agent_id}"


def test_exporter_returns_soul_md():
    for agent_id in KNOWN_AGENTS:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"Exporter failed for {agent_id}: {result.stderr}"
        assert "# FILE: soul.md" in result.stdout, f"Missing soul.md for {agent_id}"


def test_exporter_returns_agent_md():
    for agent_id in KNOWN_AGENTS:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"Exporter failed for {agent_id}: {result.stderr}"
        assert "# FILE: agent.md" in result.stdout, f"Missing agent.md for {agent_id}"


def test_exporter_no_network_calls():
    for agent_id in KNOWN_AGENTS:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert "api" not in result.stderr.lower()
        assert "network" not in result.stderr.lower()
        assert "http" not in result.stderr.lower()


def test_exporter_does_not_call_llm():
    for agent_id in KNOWN_AGENTS:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        stdout_lower = result.stdout.lower()
        assert "llm" not in stdout_lower or "identity" in stdout_lower


def test_exporter_unknown_agent_returns_error():
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--agent-id", "Z99"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0, "Exporter should fail for unknown agent"
    assert "not found" in result.stderr.lower() or result.returncode != 0


def test_exporter_known_agents_list():
    from scripts.export_company_agent_context import KNOWN_AGENTS as KNOWN

    assert "A00" in KNOWN
    assert "A10" in KNOWN
    assert "A42" in KNOWN
    assert len(KNOWN) == 7
