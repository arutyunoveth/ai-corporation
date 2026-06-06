from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _parse_markdown_table(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if set(stripped.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and cells[0].startswith("M-"):
            rows.append(cells)
    return rows


def _status_map_from_mapping() -> dict[str, str]:
    rows = _parse_markdown_table(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")
    return {row[0]: row[3] for row in rows if len(row) >= 5}


def _status_map_from_recovery_plan() -> dict[str, str]:
    rows = _parse_markdown_table(GOVERNANCE_DIR / "registry_recovery_plan.md")
    return {row[0]: row[2] for row in rows if len(row) >= 4}


def _locked_registry_ids() -> set[str]:
    rows = _parse_markdown_table(GOVERNANCE_DIR / "canonical_module_registry_locked.md")
    return {row[0] for row in rows if len(row) >= 2}


def test_locked_registry_has_explicit_status_for_every_slot():
    expected_ids = {f"M-{index:03d}" for index in range(1, 56)}
    locked_ids = _locked_registry_ids()
    mapping_statuses = _status_map_from_mapping()

    assert locked_ids == expected_ids
    assert set(mapping_statuses) == expected_ids


def test_reserved_and_reconciled_late_slots_are_consistent_across_docs():
    mapping_statuses = _status_map_from_mapping()
    recovery_plan_statuses = _status_map_from_recovery_plan()

    expected_late_statuses = {
        "M-049": "BOUNDED_IMPLEMENTED",
        "M-050": "BOUNDED_IMPLEMENTED",
        "M-052": "PLATFORM_ONLY",
        "M-053": "GOVERNANCE_ONLY",
        "M-054": "PLATFORM_ONLY",
        "M-055": "GOVERNANCE_ONLY",
    }

    for module_id, expected_status in expected_late_statuses.items():
        assert mapping_statuses[module_id] == expected_status
        assert recovery_plan_statuses[module_id] == expected_status


def test_r6_docs_remove_unresolved_mismatch_state_for_m052_through_m055():
    mapping_text = (GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md").read_text(encoding="utf-8")
    audit_text = (GOVERNANCE_DIR / "Final_Recovery_Audit.md").read_text(encoding="utf-8")
    reconciliation_text = (GOVERNANCE_DIR / "Registry_Reconciliation_R6.md").read_text(encoding="utf-8")

    assert "| M-052 | Notification Layer |" in mapping_text
    assert "| M-053 | Red Flag Registry |" in mapping_text
    assert "| M-054 | Master Dashboard |" in mapping_text
    assert "| M-055 | SaaS Productization Tracker |" in mapping_text

    assert "| M-052 | Notification Layer |" in reconciliation_text
    assert "| M-053 | Red Flag Registry |" in reconciliation_text
    assert "| M-054 | Master Dashboard |" in reconciliation_text
    assert "| M-055 | SaaS Productization Tracker |" in reconciliation_text

    assert "Current `M-052` is optimization recommendation engine" not in mapping_text
    assert "Current `M-053` is operator copilot feed" not in mapping_text
    assert "Current `M-054` is connector registry and sync backbone" not in mapping_text
    assert "Current `M-055` is operator workspace feed API" not in mapping_text
    assert "MISMATCH | 4 | M-052..M-055" not in mapping_text
    assert "Remaining platform mismatches: `M-052..M-055`" not in (
        GOVERNANCE_DIR / "registry_recovery_plan.md"
    ).read_text(encoding="utf-8")
    assert "no unresolved locked-registry mismatches remain" in audit_text.lower()


def test_m049_and_m050_are_bounded_implemented_without_broad_runtime_opening():
    mapping_text = (GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md").read_text(encoding="utf-8")
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    recovery_plan_text = (GOVERNANCE_DIR / "registry_recovery_plan.md").read_text(encoding="utf-8")

    assert "| M-049 | Agent Registry |" in mapping_text
    assert "| M-050 | Prompt / Schema Library |" in mapping_text
    assert "bounded internal metadata/control slice" in recovery_plan_text
    assert "Broad execution behavior for `M-049`, `M-050` is still deferred".lower() in recovery_plan_text.lower()
    assert "Bounded Runtime Canonical Modules" in readme_text
