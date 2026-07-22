from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from src.modules.customer_pilot import canonical_snapshot
from src.modules.customer_pilot.canonical_snapshot import (
    CanonicalSnapshotContractError,
    CanonicalSnapshotStorageError,
    publish_canonical_snapshot,
)
from src.modules.procurement_analysis.frozen_producer import (
    produce_frozen_canonical_analysis,
)


def _config(root: Path):
    return lambda: type("Config", (), {"data_dir": str(root)})()


def _verified(tmp_path: Path):
    return produce_frozen_canonical_analysis(
        registry_number="0379100000726000101",
        run_id="11111111-1111-1111-1111-111111111111",
        output_dir=tmp_path / "working",
        metadata={},
        documents=[],
        source_analysis_run_id="22222222-2222-2222-2222-222222222222",
    )


def _publish(root: Path, verified):
    return publish_canonical_snapshot(
        customer_id="CUST-A",
        project_id="11111111-1111-1111-1111-111111111111",
        procurement_case_id="33333333-3333-3333-3333-333333333333",
        run_id="44444444-4444-4444-4444-444444444444",
        registry_number="0379100000726000101",
        source_analysis_run_id=verified.source_analysis_run_id,
        verified=verified.persisted,
    )


def test_publishes_exact_verified_bytes_and_idempotently_reuses_manifest(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    production = _verified(tmp_path)
    first = _publish(tmp_path, production)
    before = first.binding_manifest_path.stat().st_mtime_ns
    second = _publish(tmp_path, production)
    assert (
        first.requirements_path.read_bytes() == production.persisted.requirements_bytes
    )
    assert (
        first.canonical_report_path.read_bytes()
        == production.persisted.canonical_report_bytes
    )
    assert second.idempotent is True
    assert second.manifest_bytes == first.manifest_bytes
    assert second.binding_manifest_path.stat().st_mtime_ns == before
    assert second.requirements_relative_path.startswith("customer-pilot/CUST-A/")


def test_conflicting_snapshot_is_never_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    production = _verified(tmp_path)
    first = _publish(tmp_path, production)
    changed = production.persisted.__class__(
        **{
            **production.persisted.__dict__,
            "requirements_bytes": production.persisted.requirements_bytes + b" ",
        }
    )
    with pytest.raises(CanonicalSnapshotContractError):
        publish_canonical_snapshot(
            customer_id="CUST-A",
            project_id="11111111-1111-1111-1111-111111111111",
            procurement_case_id="33333333-3333-3333-3333-333333333333",
            run_id="44444444-4444-4444-4444-444444444444",
            registry_number="0379100000726000101",
            source_analysis_run_id=production.source_analysis_run_id,
            verified=changed,
        )
    assert (
        first.requirements_path.read_bytes() == production.persisted.requirements_bytes
    )


def test_symlinked_namespace_is_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    production = _verified(tmp_path)
    (tmp_path / "customer-pilot").symlink_to(tmp_path / "elsewhere")
    with pytest.raises(CanonicalSnapshotStorageError):
        _publish(tmp_path, production)


def test_concurrent_identical_publication_returns_one_immutable_generation(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    production = _verified(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        snapshots = list(pool.map(lambda _: _publish(tmp_path, production), range(2)))
    assert sorted(item.idempotent for item in snapshots) == [False, True]
    assert snapshots[0].manifest_bytes == snapshots[1].manifest_bytes


def test_pre_rename_fault_leaves_no_final_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(canonical_snapshot, "load_config", _config(tmp_path))
    production = _verified(tmp_path)

    def fault(point: str):
        if point == "before_rename":
            raise CanonicalSnapshotStorageError("injected")

    with pytest.raises(CanonicalSnapshotStorageError):
        publish_canonical_snapshot(
            customer_id="CUST-A",
            project_id="11111111-1111-1111-1111-111111111111",
            procurement_case_id="33333333-3333-3333-3333-333333333333",
            run_id="44444444-4444-4444-4444-444444444444",
            registry_number="0379100000726000101",
            source_analysis_run_id=production.source_analysis_run_id,
            verified=production.persisted,
            fault=fault,
        )
    assert not (
        tmp_path
        / "customer-pilot"
        / "CUST-A"
        / "11111111-1111-1111-1111-111111111111"
        / "33333333-3333-3333-3333-333333333333"
        / "44444444-4444-4444-4444-444444444444"
        / "analysis"
    ).exists()
