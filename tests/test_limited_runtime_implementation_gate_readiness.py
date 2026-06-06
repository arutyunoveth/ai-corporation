from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mvp_implementation_readiness_docs_exist():
    required_docs = [
        LAUNCH_DIR / "MVP_Implementation_Readiness_Checklist.md",
        LAUNCH_DIR / "MVP_Implementation_Delivery_Sequence.md",
        LAUNCH_DIR / "MVP_Implementation_Acceptance_Criteria.md",
        LAUNCH_DIR / "MVP_Implementation_Rollback_Boundaries.md",
        LAUNCH_DIR / "MVP_Implementation_Test_Strategy.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing G1-S3 deliverable: {path.name}"


def test_readiness_docs_keep_execution_behavior_out_of_scope():
    readme_text = _read(REPO_ROOT / "README.md")
    sequence_text = _read(LAUNCH_DIR / "MVP_Implementation_Delivery_Sequence.md")
    acceptance_text = _read(LAUNCH_DIR / "MVP_Implementation_Acceptance_Criteria.md")
    rollback_text = _read(LAUNCH_DIR / "MVP_Implementation_Rollback_Boundaries.md")

    assert "MVP implementation package is now ready for execution planning." in readme_text
    assert "does **not** include" in sequence_text
    assert "agent execution" in acceptance_text
    assert "introduction of execution behavior" in rollback_text
