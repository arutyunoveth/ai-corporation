"""
Tests for the active procurement measurement module (ARV-009C1).
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pytest

from scripts.capacity.planning.measure_active_procurements import (
    MAX_PROCESSING_CONCURRENCY,
    NON_ACTIVE_STATUSES,
    ONE_GIB,
    PERSISTENT_RESULTS_AND_LOGS,
    PROCESSING_SPACE_MIN,
    TWO_TB,
    COMMERCIAL_RESERVE_RATIO,
    EIS_SOURCES,
    DocumentInfo,
    PackageInfo,
    SnapshotStats,
    SizingResult,
    compute_sizing,
    compute_statistics,
    format_bytes,
    is_procurement_active,
    run_demo,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_packages() -> list[PackageInfo]:
    rng = random.Random(42)
    pkgs = []
    for i in range(50):
        doc_count = rng.randint(1, 5)
        docs = [
            DocumentInfo(
                file_name=f"doc_{d}.pdf",
                size_bytes=rng.randint(10_000, 50_000_000),
                content_type="application/pdf",
                is_archive=False,
                source="synthetic",
            )
            for d in range(doc_count)
        ]
        pkgs.append(PackageInfo(
            tender_id=f"test-{i:04d}",
            registry_number=f"TEST{i:019d}",
            law_type=rng.choice(list(EIS_SOURCES)),
            status="applying",
            source="demo",
            documents=docs,
        ))
    pkgs.sort(key=lambda p: p.total_bytes, reverse=True)
    return pkgs


@pytest.fixture
def single_stat(sample_packages: list[PackageInfo]) -> SnapshotStats:
    return compute_statistics(sample_packages, snapshot_index=1)


# ─── Active procurement filtering ────────────────────────────────────────

class TestActiveProcurementFilter:
    def test_active_status(self):
        assert is_procurement_active("published") is True
        assert is_procurement_active("applying") is True
        assert is_procurement_active("active") is True

    def test_non_active_statuses(self):
        for status in NON_ACTIVE_STATUSES:
            assert is_procurement_active(status) is False, f"{status!r} should be non-active"

    def test_none_status(self):
        assert is_procurement_active(None) is False

    def test_empty_status(self):
        assert is_procurement_active("") is False

    def test_case_insensitive(self):
        assert is_procurement_active("CANCELLED") is False
        assert is_procurement_active("PUBLISHED") is True


# ─── Statistics computation ───────────────────────────────────────────────

class TestStatistics:
    def test_empty_packages(self):
        stats = compute_statistics([])
        assert stats.total_tenders == 0
        assert stats.total_bytes == 0
        assert stats.mean_bytes == 0.0
        assert stats.p50_bytes == 0

    def test_single_package(self):
        doc = DocumentInfo("test.pdf", 1_000_000, "application/pdf", False, "test")
        pkg = PackageInfo("t1", "RN1", "44fz", "published", "test", [doc])
        stats = compute_statistics([pkg])
        assert stats.total_tenders == 1
        assert stats.total_bytes == 1_000_000
        assert stats.p50_bytes == 1_000_000
        assert stats.p99_bytes == 1_000_000

    def test_percentiles(self, sample_packages: list[PackageInfo]):
        stats = compute_statistics(sample_packages, snapshot_index=1)
        sizes = sorted([p.total_bytes for p in sample_packages])
        n = len(sizes)
        p50_idx = max(0, min(n - 1, int(math.ceil(50 * n / 100) - 1)))
        p95_idx = max(0, min(n - 1, int(math.ceil(95 * n / 100) - 1)))
        expected_p50 = sizes[p50_idx]
        expected_p95 = sizes[p95_idx]
        assert stats.p50_bytes == expected_p50
        assert stats.p95_bytes == expected_p95

    def test_snapshot_index(self):
        stats = compute_statistics([], snapshot_index=3)
        assert stats.snapshot_index == 3

    def test_snapshot_date(self):
        stats = compute_statistics([], snapshot_date="2026-07-24")
        assert stats.snapshot_date == "2026-07-24"


# ─── Heavy-tail contribution ──────────────────────────────────────────────

class TestHeavyTail:
    def test_top_1_pct_below_100(self):
        sizes = [100_000_000] * 200
        pkgs = [PackageInfo(
            tender_id=f"t{i}", registry_number=None, law_type="44fz",
            status="published", source="test",
            documents=[DocumentInfo(f"d.pdf", s, "application/pdf", False, "test")],
        ) for i, s in enumerate(sizes)]
        stats = compute_statistics(pkgs)
        assert 0 < stats.heavy_tail_top_1_pct <= 1.0

    def test_heavy_tail_monotonic(self, single_stat: SnapshotStats):
        assert single_stat.heavy_tail_top_1_pct <= single_stat.heavy_tail_top_5_pct
        assert single_stat.heavy_tail_top_5_pct <= single_stat.heavy_tail_top_10_pct

    def test_heavy_tail_empty(self):
        stats = compute_statistics([])
        assert stats.heavy_tail_top_1_pct == 0.0
        assert stats.heavy_tail_top_5_pct == 0.0
        assert stats.heavy_tail_top_10_pct == 0.0


# ─── Large package counting ───────────────────────────────────────────────

class TestLargePackages:
    def test_over_100mb(self):
        sizes = [50_000_000, 150_000_000, 200_000_000]
        pkgs = [PackageInfo(f"t{i}", None, "44fz", "published", "test",
                            [DocumentInfo("d.pdf", s, "application/pdf", False, "test")])
                for i, s in enumerate(sizes)]
        stats = compute_statistics(pkgs)
        assert stats.packages_over_100mb == 2

    def test_over_1gb(self):
        sizes = [500_000_000, ONE_GIB + 1]
        pkgs = [PackageInfo(f"t{i}", None, "44fz", "published", "test",
                            [DocumentInfo("d.pdf", s, "application/pdf", False, "test")])
                for i, s in enumerate(sizes)]
        stats = compute_statistics(pkgs)
        assert stats.packages_over_1gb == 1


# ─── Sizing calculation ───────────────────────────────────────────────────

class TestSizing:
    def test_50_pct_commercial_reserve(self):
        stats = SnapshotStats(
            snapshot_date="2026-07-24", snapshot_index=1,
            total_tenders=100, total_documents=500,
            total_bytes=100_000_000_000, mean_bytes=1_000_000_000.0,
            p50_bytes=500_000_000, p75_bytes=1_000_000_000,
            p90_bytes=2_000_000_000, p95_bytes=3_000_000_000,
            p99_bytes=5_000_000_000, max_bytes=10_000_000_000,
            pct_over_100mb=50.0, pct_over_250mb=20.0,
            pct_over_500mb=5.0, pct_over_1gb=0.0,
            heavy_tail_top_1_pct=0.1, heavy_tail_top_5_pct=0.3,
            heavy_tail_top_10_pct=0.5, packages_over_100mb=50,
            packages_over_250mb=20, packages_over_500mb=5, packages_over_1gb=0,
        )
        sizing = compute_sizing([stats])
        expected_reserve = int(100_000_000_000 * COMMERCIAL_RESERVE_RATIO)
        assert sizing.commercial_reserve_bytes == expected_reserve

    def test_green_threshold(self):
        stats = SnapshotStats(
            snapshot_date="2026-07-24", snapshot_index=1,
            total_tenders=100, total_documents=300,
            total_bytes=500_000_000_000, mean_bytes=5_000_000_000.0,
            p50_bytes=2_000_000_000, p75_bytes=5_000_000_000,
            p90_bytes=10_000_000_000, p95_bytes=15_000_000_000,
            p99_bytes=20_000_000_000, max_bytes=30_000_000_000,
            pct_over_100mb=30.0, pct_over_250mb=10.0,
            pct_over_500mb=2.0, pct_over_1gb=0.0,
            heavy_tail_top_1_pct=0.05, heavy_tail_top_5_pct=0.2,
            heavy_tail_top_10_pct=0.4, packages_over_100mb=30,
            packages_over_250mb=10, packages_over_500mb=2, packages_over_1gb=0,
        )
        sizing = compute_sizing([stats])
        assert sizing.classification == "GREEN"

    def test_yellow_threshold(self):
        total = 900_000_000_000
        stats = SnapshotStats(
            snapshot_date="2026-07-24", snapshot_index=1,
            total_tenders=100, total_documents=300,
            total_bytes=total, mean_bytes=float(total / 100),
            p50_bytes=10_000_000_000, p75_bytes=20_000_000_000,
            p90_bytes=30_000_000_000, p95_bytes=40_000_000_000,
            p99_bytes=50_000_000_000, max_bytes=60_000_000_000,
            pct_over_100mb=30.0, pct_over_250mb=10.0,
            pct_over_500mb=2.0, pct_over_1gb=0.0,
            heavy_tail_top_1_pct=0.05, heavy_tail_top_5_pct=0.2,
            heavy_tail_top_10_pct=0.4, packages_over_100mb=30,
            packages_over_250mb=10, packages_over_500mb=2, packages_over_1gb=0,
        )
        sizing = compute_sizing([stats])
        assert sizing.classification == "YELLOW"
        assert sizing.base_required > int(1.4 * TWO_TB / 2)
        assert sizing.base_required <= int(1.7 * TWO_TB / 2)

    def test_red_threshold(self):
        total = 1_800_000_000_000  # ~1.8 TB
        stats = SnapshotStats(
            snapshot_date="2026-07-24", snapshot_index=1,
            total_tenders=100, total_documents=300,
            total_bytes=total, mean_bytes=float(total / 100),
            p50_bytes=10_000_000_000, p75_bytes=20_000_000_000,
            p90_bytes=30_000_000_000, p95_bytes=40_000_000_000,
            p99_bytes=50_000_000_000, max_bytes=60_000_000_000,
            pct_over_100mb=30.0, pct_over_250mb=10.0,
            pct_over_500mb=2.0, pct_over_1gb=0.0,
            heavy_tail_top_1_pct=0.05, heavy_tail_top_5_pct=0.2,
            heavy_tail_top_10_pct=0.4, packages_over_100mb=30,
            packages_over_250mb=10, packages_over_500mb=2, packages_over_1gb=0,
        )
        sizing = compute_sizing([stats])
        assert sizing.classification == "RED"

    def test_processing_space_min(self):
        stats = SnapshotStats(
            snapshot_date="2026-07-24", snapshot_index=1,
            total_tenders=1, total_documents=1,
            total_bytes=1_000, mean_bytes=1000.0,
            p50_bytes=1000, p75_bytes=1000,
            p90_bytes=1000, p95_bytes=1000,
            p99_bytes=1000, max_bytes=1000,
            pct_over_100mb=0.0, pct_over_250mb=0.0,
            pct_over_500mb=0.0, pct_over_1gb=0.0,
            heavy_tail_top_1_pct=0.0, heavy_tail_top_5_pct=0.0,
            heavy_tail_top_10_pct=0.0,
            packages_over_100mb=0, packages_over_250mb=0,
            packages_over_500mb=0, packages_over_1gb=0,
        )
        sizing = compute_sizing([stats])
        assert sizing.processing_space_bytes == PROCESSING_SPACE_MIN

    def test_processing_space_p99(self):
        p99 = 100_000_000_000  # 100 GiB
        stats = SnapshotStats(
            snapshot_date="2026-07-24", snapshot_index=1,
            total_tenders=1, total_documents=1,
            total_bytes=1_000, mean_bytes=1000.0,
            p50_bytes=1000, p75_bytes=1000,
            p90_bytes=1000, p95_bytes=1000,
            p99_bytes=p99, max_bytes=p99,
            pct_over_100mb=0.0, pct_over_250mb=0.0,
            pct_over_500mb=0.0, pct_over_1gb=0.0,
            heavy_tail_top_1_pct=0.0, heavy_tail_top_5_pct=0.0,
            heavy_tail_top_10_pct=0.0,
            packages_over_100mb=0, packages_over_250mb=0,
            packages_over_500mb=0, packages_over_1gb=0,
        )
        sizing = compute_sizing([stats])
        expected = p99 * MAX_PROCESSING_CONCURRENCY
        assert sizing.processing_space_bytes == expected

    def test_persistent_results_constant(self):
        stats = SnapshotStats(
            snapshot_date="2026-07-24", snapshot_index=1,
            total_tenders=0, total_documents=0,
            total_bytes=0, mean_bytes=0.0,
            p50_bytes=0, p75_bytes=0, p90_bytes=0, p95_bytes=0,
            p99_bytes=0, max_bytes=0,
            pct_over_100mb=0.0, pct_over_250mb=0.0,
            pct_over_500mb=0.0, pct_over_1gb=0.0,
            heavy_tail_top_1_pct=0.0, heavy_tail_top_5_pct=0.0,
            heavy_tail_top_10_pct=0.0,
            packages_over_100mb=0, packages_over_250mb=0,
            packages_over_500mb=0, packages_over_1gb=0,
        )
        sizing = compute_sizing([stats])
        assert sizing.persistent_results_and_logs == PERSISTENT_RESULTS_AND_LOGS

    def test_max_snapshot_selection(self):
        stats1 = SnapshotStats(
            snapshot_date="day1", snapshot_index=1,
            total_tenders=1, total_documents=1,
            total_bytes=100, mean_bytes=100.0,
            p50_bytes=100, p75_bytes=100,
            p90_bytes=100, p95_bytes=100,
            p99_bytes=100, max_bytes=100,
            pct_over_100mb=0.0, pct_over_250mb=0.0,
            pct_over_500mb=0.0, pct_over_1gb=0.0,
            heavy_tail_top_1_pct=0.0, heavy_tail_top_5_pct=0.0,
            heavy_tail_top_10_pct=0.0,
            packages_over_100mb=0, packages_over_250mb=0,
            packages_over_500mb=0, packages_over_1gb=0,
        )
        stats2 = SnapshotStats(
            snapshot_date="day2", snapshot_index=2,
            total_tenders=1, total_documents=1,
            total_bytes=200, mean_bytes=200.0,
            p50_bytes=200, p75_bytes=200,
            p90_bytes=200, p95_bytes=200,
            p99_bytes=200, max_bytes=200,
            pct_over_100mb=0.0, pct_over_250mb=0.0,
            pct_over_500mb=0.0, pct_over_1gb=0.0,
            heavy_tail_top_1_pct=0.0, heavy_tail_top_5_pct=0.0,
            heavy_tail_top_10_pct=0.0,
            packages_over_100mb=0, packages_over_250mb=0,
            packages_over_500mb=0, packages_over_1gb=0,
        )
        sizing = compute_sizing([stats1, stats2])
        assert sizing.eis_active_bytes == 200
        assert sizing.max_snapshot_bytes == 200

    def test_empty_stats_list(self):
        sizing = compute_sizing([])
        assert sizing.snapshot_count == 0
        assert sizing.classification == "GREEN"


# ─── Privacy ──────────────────────────────────────────────────────────────

class TestPrivacy:
    def test_no_tender_ids_in_output(self, tmp_path: Path):
        stats_list = run_demo(tmp_path, snapshot_series=False)
        json_file = tmp_path / "arv-009-active-snapshot-summary.json"
        with open(json_file) as f:
            data = json.load(f)
        text = json.dumps(data)
        assert "demo-" not in text
        assert "TEST" not in text

    def test_no_registry_numbers_in_summary(self, tmp_path: Path):
        stats_list = run_demo(tmp_path, snapshot_series=False)
        json_file = tmp_path / "arv-009-active-snapshot-summary.json"
        with open(json_file) as f:
            data = json.load(f)
        assert "registry_number" not in json.dumps(data)


# ─── Determinism ──────────────────────────────────────────────────────────

class TestDeterminism:
    def test_json_deterministic(self, tmp_path: Path):
        p1 = tmp_path / "run1"
        p2 = tmp_path / "run2"
        run_demo(p1, snapshot_series=True)
        run_demo(p2, snapshot_series=True)

        with open(p1 / "arv-009-active-snapshot-summary.json") as f:
            d1 = json.load(f)
        with open(p2 / "arv-009-active-snapshot-summary.json") as f:
            d2 = json.load(f)
        d1["meta"]["generated_at"] = ""
        d2["meta"]["generated_at"] = ""
        assert d1 == d2

    def test_csv_deterministic(self, tmp_path: Path):
        p1 = tmp_path / "run1"
        p2 = tmp_path / "run2"
        run_demo(p1, snapshot_series=True)
        run_demo(p2, snapshot_series=True)

        csv1 = (p1 / "arv-009-active-snapshot-summary.csv").read_text()
        csv2 = (p2 / "arv-009-active-snapshot-summary.csv").read_text()
        assert csv1 == csv2


# ─── Demo mode ────────────────────────────────────────────────────────────

class TestDemoMode:
    def test_single_snapshot(self, tmp_path: Path):
        stats_list = run_demo(tmp_path, snapshot_series=False)
        assert len(stats_list) == 1
        assert stats_list[0].total_tenders > 0
        assert stats_list[0].total_bytes > 0

    def test_snapshot_series(self, tmp_path: Path):
        stats_list = run_demo(tmp_path, snapshot_series=True)
        assert len(stats_list) == 3
        # Each snapshot should have increasing tenders
        assert stats_list[0].total_tenders < stats_list[1].total_tenders
        assert stats_list[1].total_tenders < stats_list[2].total_tenders

    def test_files_created(self, tmp_path: Path):
        run_demo(tmp_path, snapshot_series=True)
        assert (tmp_path / "arv-009-active-snapshot-summary.json").exists()
        assert (tmp_path / "arv-009-active-snapshot-summary.csv").exists()
        assert (tmp_path / "snapshot-1-sanitized-manifest.json").exists()
        assert (tmp_path / "snapshot-2-sanitized-manifest.json").exists()
        assert (tmp_path / "snapshot-3-sanitized-manifest.json").exists()


# ─── Format helper ────────────────────────────────────────────────────────

class TestFormatBytes:
    def test_bytes(self):
        assert format_bytes(500) == "500 B"

    def test_kb(self):
        assert format_bytes(1_500) == "1.5 KB"

    def test_mb(self):
        assert format_bytes(1_500_000) == "1.5 MB"

    def test_gib(self):
        assert "GiB" in format_bytes(ONE_GIB)
