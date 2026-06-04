from pathlib import Path

from src.modules.event_log.models import EventRecord
from src.modules.launch_visibility.models import LaunchVisibilityItem, LaunchVisibilityRecord, LaunchVisibilitySet
from tests.test_recovery_r5_integration import _prepare_r5_final_context


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_build_deal_launch_visibility_and_persist_items(client, session):
    package = _prepare_r5_final_context(client, session)
    deal_id = package["intake"]["deal_id"]

    response = client.post(
        "/launch-visibility/build",
        json={"scope_type": "DEAL", "scope_ref": deal_id},
    )
    assert response.status_code == 201
    payload = response.json()

    visibility_set = session.query(LaunchVisibilitySet).filter_by(
        launch_visibility_set_id=payload["launch_visibility_set_id"]
    ).one()
    visibility_record = session.query(LaunchVisibilityRecord).filter_by(
        launch_visibility_set_id=payload["launch_visibility_set_id"]
    ).one()
    visibility_items = session.query(LaunchVisibilityItem).filter_by(
        launch_visibility_id=visibility_record.launch_visibility_id
    ).all()

    assert visibility_set.scope_type == "DEAL"
    assert visibility_set.scope_ref == deal_id
    assert visibility_record.active_deal_count == 1
    assert visibility_record.red_flag_count >= 2
    assert visibility_record.attention_count >= 1
    assert visibility_record.manual_review_count >= 1
    assert len(visibility_items) >= 4


def test_red_flag_aggregation_includes_multiple_sources(client, session):
    package = _prepare_r5_final_context(client, session)
    deal_id = package["intake"]["deal_id"]

    response = client.post(
        "/launch-visibility/build",
        json={"scope_type": "DEAL", "scope_ref": deal_id},
    )
    assert response.status_code == 201
    record = response.json()["records"][0]

    source_modules = {item["source_module_id"] for item in record["items"] if item["source_module_id"]}

    assert "M-040" in source_modules
    assert "M-043" in source_modules
    assert "M-044" in source_modules


def test_build_pilot_launch_visibility_and_write_events(client, session):
    package = _prepare_r5_final_context(client, session)
    deal_id = package["intake"]["deal_id"]

    response = client.post(
        "/launch-visibility/build",
        json={"scope_type": "PILOT", "scope_ref": "L1-PILOT"},
    )
    assert response.status_code == 201
    payload = response.json()
    record = payload["records"][0]

    assert payload["scope_type"] == "PILOT"
    assert record["active_deal_count"] >= 1
    assert record["blocked_deal_count"] >= 1
    assert any(item["deal_id"] == deal_id for item in record["items"])

    event_codes = {event.event_code for event in session.query(EventRecord).all()}
    assert "launch_visibility_built" in event_codes
    assert "launch_visibility_item_recorded" in event_codes


def test_pre_l1_docs_and_readme_remain_honest_about_scope():
    required_docs = [
        LAUNCH_DIR / "Pre_L1_Ops_Visibility_Package.md",
        LAUNCH_DIR / "Pre_L1_Attention_and_Red_Flags.md",
        LAUNCH_DIR / "Pre_L1_Owner_Overview.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing pre-L1 launch doc: {path.name}"

    readme_text = _read(REPO_ROOT / "README.md")
    package_text = _read(LAUNCH_DIR / "Pre_L1_Ops_Visibility_Package.md")
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")

    assert "pre-L1 ops visibility" in readme_text
    assert "does **not** open" in package_text
    assert "M-049" in package_text
    assert "M-050" in package_text
    assert "| M-052 | Notification Layer |" in mapping_text
    assert "| M-053 | Red Flag Registry |" in mapping_text
    assert "| M-054 | Master Dashboard |" in mapping_text
    assert "| M-055 | SaaS Productization Tracker |" in mapping_text
