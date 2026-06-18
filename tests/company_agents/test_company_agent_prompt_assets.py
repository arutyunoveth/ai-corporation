from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPANY_AGENTS_DIR = REPO_ROOT / "docs" / "agents" / "company"

AGENT_DIRS = [
    "A00_chief_of_staff",
    "A10_tender_operator",
    "A11_rfq_supplier_analyst",
    "A20_finance_unit_economics",
    "A21_legal_contract_risk",
    "A40_cto_system_architect",
    "A42_qa_release",
]

REQUIRED_FILES = ["identity.md", "soul.md", "agent.md"]


def test_all_active_agent_dirs_exist():
    for agent_dir in AGENT_DIRS:
        path = COMPANY_AGENTS_DIR / agent_dir
        assert path.is_dir(), f"Missing agent directory: {agent_dir}"


def test_all_active_agent_files_exist():
    for agent_dir in AGENT_DIRS:
        for filename in REQUIRED_FILES:
            path = COMPANY_AGENTS_DIR / agent_dir / filename
            assert path.is_file(), f"Missing file: {agent_dir}/{filename}"


def test_identity_files_have_required_frontmatter():
    for agent_dir in AGENT_DIRS:
        identity_path = COMPANY_AGENTS_DIR / agent_dir / "identity.md"
        content = identity_path.read_text(encoding="utf-8")
        assert "agent_id:" in content, f"{agent_dir}/identity.md missing agent_id frontmatter"
        assert "execution_allowed: false" in content, f"{agent_dir}/identity.md missing execution_allowed: false"
        assert "runtime_mode:" in content, f"{agent_dir}/identity.md missing runtime_mode"


def test_agent_files_have_mission_section():
    for agent_dir in AGENT_DIRS:
        agent_path = COMPANY_AGENTS_DIR / agent_dir / "agent.md"
        content = agent_path.read_text(encoding="utf-8")
        assert "## Mission" in content, f"{agent_dir}/agent.md missing Mission section"
        assert "## Responsibilities" in content, f"{agent_dir}/agent.md missing Responsibilities section"
        assert "## Forbidden Actions" in content, f"{agent_dir}/agent.md missing Forbidden Actions section"
