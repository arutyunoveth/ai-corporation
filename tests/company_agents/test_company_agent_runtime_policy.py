from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_policy_doc_exists():
    policy_path = REPO_ROOT / "docs" / "agents" / "company" / "Company_Agent_Runtime_Policy.md"
    assert policy_path.is_file(), "Company Agent Runtime Policy doc not found"


def test_policy_doc_states_sequential_execution():
    policy_path = REPO_ROOT / "docs" / "agents" / "company" / "Company_Agent_Runtime_Policy.md"
    content = policy_path.read_text(encoding="utf-8")
    assert "sequential execution" in content.lower()


def test_policy_doc_states_no_autonomous_execution():
    policy_path = REPO_ROOT / "docs" / "agents" / "company" / "Company_Agent_Runtime_Policy.md"
    content = policy_path.read_text(encoding="utf-8")
    assert "autonomous execution" in content.lower()
    assert "does not implement" in content.lower()


def test_policy_doc_states_no_cloud_dispatch():
    policy_path = REPO_ROOT / "docs" / "agents" / "company" / "Company_Agent_Runtime_Policy.md"
    content = policy_path.read_text(encoding="utf-8")
    assert "cloud dispatch" in content.lower()


def test_policy_doc_states_max_parallel_is_one():
    policy_path = REPO_ROOT / "docs" / "agents" / "company" / "Company_Agent_Runtime_Policy.md"
    content = policy_path.read_text(encoding="utf-8")
    assert "max_parallel_local_agents = 1" in content


def test_governance_doc_exists():
    governance_path = REPO_ROOT / "docs" / "00_architecture" / "company_agents_metadata_extension.md"
    assert governance_path.is_file(), "Company agents governance doc not found"


def test_governance_doc_states_no_new_canonical_modules():
    governance_path = REPO_ROOT / "docs" / "00_architecture" / "company_agents_metadata_extension.md"
    content = governance_path.read_text(encoding="utf-8")
    assert "new canonical modules" in content.lower()
    assert "does not introduce" in content.lower()
