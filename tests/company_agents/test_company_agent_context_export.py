import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT_SCRIPT = REPO_ROOT / "scripts" / "export_company_agent_context.py"

KNOWN_AGENTS = ["A00", "A10", "A11", "A20", "A21", "A40", "A42"]


def test_exporter_runs_for_all_active_agents():
    for agent_id in KNOWN_AGENTS:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"Exporter failed for {agent_id}: {result.stderr}"
        assert "identity.md" in result.stdout, f"Exporter output missing identity.md for {agent_id}"
        assert "soul.md" in result.stdout, f"Exporter output missing soul.md for {agent_id}"
        assert "agent.md" in result.stdout, f"Exporter output missing agent.md for {agent_id}"


def test_exporter_returns_error_for_unknown_agent():
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--agent-id", "Z99"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0, "Exporter should fail for unknown agent"


def test_exporter_does_not_call_llm():
    for agent_id in KNOWN_AGENTS:
        result = subprocess.run(
            [sys.executable, str(EXPORT_SCRIPT), "--agent-id", agent_id],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert "llm" not in result.stdout.lower() or "identity" in result.stdout.lower()
        assert "api" not in result.stderr.lower()
        assert "network" not in result.stderr.lower()
