from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cp0_acceptance_audit_exists_and_references_required_state():
    audit_path = ROOT / "docs" / "product" / "CP0_Repository_Sync_Acceptance_Audit.md"
    assert audit_path.exists()

    audit_text = audit_path.read_text(encoding="utf-8")
    assert "df58806" in audit_text
    assert "301 passed, 1 warning" in audit_text
    assert "Local repository acceptance is confirmed." in audit_text
    assert "origin/main" in audit_text
    assert "Proceed to `CP1" in audit_text
