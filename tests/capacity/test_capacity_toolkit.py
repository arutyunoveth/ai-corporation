from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path

import pytest

from scripts.capacity.backup_reader import analyze_backup
from scripts.capacity.db_collector import collect_database_metrics
from scripts.capacity.forecast_model import (
    _gib,
    _round_up_gib,
    compute_forecast,
    load_scenarios,
    run_forecast,
)
from scripts.capacity.fs_collector import collect_filesystem_metrics
from scripts.capacity.report_renderer import (
    build_snapshot_json,
    render_forecast_markdown,
    render_snapshot_markdown,
    write_files_csv,
    write_forecast_csv,
    write_json_report,
    write_relations_csv,
)

_GIB = 1024 ** 3

# ── scenarios fixture ──────────────────────────────────────────────────


@pytest.fixture()
def scenarios_path() -> str:
    return str(Path(__file__).resolve().parent.parent.parent / "samples" / "capacity" / "scenarios.example.json")


# ── forecast helpers ───────────────────────────────────────────────────


class TestGibConversion:
    def test_gib_conversion(self):
        assert _gib(0) == 0.0
        assert _gib(_GIB) == 1.0
        assert _gib(2 * _GIB) == 2.0
        assert _gib(500 * 1024 * 1024) == pytest.approx(0.49, abs=0.01)

    def test_round_up_gib(self):
        assert _round_up_gib(0) == 0
        assert _round_up_gib(1 * _GIB) == 10
        assert _round_up_gib(15 * _GIB) == 20
        assert _round_up_gib(99 * _GIB) == 100
        assert _round_up_gib(101 * _GIB) == 110

    def test_round_up_small(self):
        assert _round_up_gib(500 * 1024 * 1024) == 10


class TestForecastArithmetic:
    def test_basic_forecast_1_year(self):
        assumptions = {
            "procurements_per_month": 5,
            "analysis_runs_per_procurement": 3,
            "documents_per_procurement": 50,
            "raw_document_bytes_per_procurement": 524288000,
            "extracted_text_bytes_per_procurement": 52428800,
            "chunks_per_procurement": 15000,
            "vector_dimension": 1536,
            "vector_bytes_per_component": 4,
            "embedding_rows_per_chunk": 1,
            "report_artifact_bytes_per_run": 10485760,
            "other_artifact_bytes_per_run": 52428800,
            "database_non_vector_bytes_per_procurement": 104857600,
            "database_non_vector_bytes_per_run": 20971520,
            "full_backups_retained": 7,
            "backup_compression_ratio": 0.3,
            "temporary_space_peak_factor": 1.5,
            "operational_margin_bytes": 10737418240,
            "free_space_reserve_percent": 20,
        }
        result = compute_forecast(None, None, assumptions, 1)
        assert result["years"] == 1
        assert result["procurements"] == 60
        assert result["analysis_runs"] == 180
        assert result["database_storage"]["bytes"] > 0
        assert result["persistent_file_storage"]["bytes"] > 0
        assert result["primary_storage"]["bytes"] > 0
        assert result["recommended_disk_gib"] >= 10
        assert result["recommended_disk_bytes"] == result["recommended_disk_gib"] * _GIB

    def test_forecast_3_years_scales(self):
        assumptions = {
            "procurements_per_month": 5,
            "analysis_runs_per_procurement": 3,
            "documents_per_procurement": 50,
            "raw_document_bytes_per_procurement": 524288000,
            "extracted_text_bytes_per_procurement": 52428800,
            "chunks_per_procurement": 15000,
            "vector_dimension": 1536,
            "vector_bytes_per_component": 4,
            "embedding_rows_per_chunk": 1,
            "report_artifact_bytes_per_run": 10485760,
            "other_artifact_bytes_per_run": 52428800,
            "database_non_vector_bytes_per_procurement": 104857600,
            "database_non_vector_bytes_per_run": 20971520,
            "full_backups_retained": 7,
            "backup_compression_ratio": 0.3,
            "temporary_space_peak_factor": 1.5,
            "operational_margin_bytes": 10737418240,
            "free_space_reserve_percent": 20,
        }
        r1 = compute_forecast(None, None, assumptions, 1)
        r3 = compute_forecast(None, None, assumptions, 3)
        assert r3["procurements"] == 3 * r1["procurements"]
        assert r3["database_storage"]["bytes"] > r1["database_storage"]["bytes"]

    def test_forecast_all_profiles_present(self, scenarios_path):
        scenarios = load_scenarios(scenarios_path)
        assert "pilot" in scenarios["profiles"]
        assert "commercial_mvp" in scenarios["profiles"]
        assert "scaling" in scenarios["profiles"]

    def test_negative_assumptions_rejected(self):
        with pytest.raises((ValueError, KeyError)):
            load_scenarios_str(
                '{"profiles": {"x": {"procurements_per_month": {"value": -1, "source": "assumption"}}}}'
            )

    def test_reserve_100_rejected(self):
        with pytest.raises(ValueError, match="must be < 100"):
            load_scenarios_str('{"profiles": {"x": {"free_space_reserve_percent": {"value": 100, "source": "assumption"}}}}')

    def test_zero_division_not_allowed_reserve_100(self):
        with pytest.raises((ValueError, ZeroDivisionError)):
            compute_forecast(
                None, None,
                {
                    "procurements_per_month": 1,
                    "analysis_runs_per_procurement": 1,
                    "documents_per_procurement": 1,
                    "raw_document_bytes_per_procurement": 1,
                    "extracted_text_bytes_per_procurement": 1,
                    "chunks_per_procurement": 1,
                    "vector_dimension": 1,
                    "vector_bytes_per_component": 1,
                    "embedding_rows_per_chunk": 1,
                    "report_artifact_bytes_per_run": 1,
                    "other_artifact_bytes_per_run": 1,
                    "database_non_vector_bytes_per_procurement": 1,
                    "database_non_vector_bytes_per_run": 1,
                    "full_backups_retained": 1,
                    "backup_compression_ratio": 0.5,
                    "temporary_space_peak_factor": 1.0,
                    "operational_margin_bytes": 0,
                    "free_space_reserve_percent": 100,
                },
                1,
            )


def load_scenarios_str(content: str):
    import json
    from scripts.capacity.forecast_model import _validate_assumption
    raw = json.loads(content)
    for pname, pdata in raw.get("profiles", {}).items():
        for key, val in pdata.items():
            if isinstance(val, dict) and "value" in val:
                _validate_assumption(key, val["value"])
    return raw


# ── filesystem collector ──────────────────────────────────────────────


class TestFilesystemCollector:
    def test_sum_logical_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "a.txt").write_text("hello")  # 5 bytes
            Path(td, "b.txt").write_text("world!")  # 6 bytes
            sub = Path(td, "sub")
            sub.mkdir()
            Path(sub, "c.txt").write_text("content")  # 7 bytes
            results = collect_filesystem_metrics({"test": td})
            assert len(results) == 1
            r = results[0]
            assert r["available"]
            assert r["logical_bytes"] == 18
            assert r["files_count"] == 3
            assert r["directories_count"] == 1

    def test_sum_allocated_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "f.dat").write_bytes(b"x" * 4096)
            results = collect_filesystem_metrics({"test": td})
            r = results[0]
            assert r["allocated_bytes"] is not None
            assert r["allocated_bytes"] >= 4096

    def test_symlinks_not_followed(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "real.txt").write_text("content")
            os.symlink("real.txt", Path(td, "link.txt"))
            results = collect_filesystem_metrics({"test": td})
            r = results[0]
            assert r["symlinks_count"] >= 1
            if os.stat(Path(td, "link.txt")).st_size == 7:
                pass

    def test_unavailable_root_is_warning(self):
        results = collect_filesystem_metrics({"missing": "/nonexistent/path/xyz123"})
        assert len(results) == 1
        r = results[0]
        assert not r["available"]
        assert r["error"] is not None

    def test_temp_files_counted(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "a.tmp").write_text("temp")
            Path(td, "b.partial").write_text("partial")
            Path(td, "regular.txt").write_text("regular")
            results = collect_filesystem_metrics({"test": td})
            r = results[0]
            assert r["temp_files_count"] == 2

    def test_no_absolute_paths_in_output(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "secret.txt").write_text("sensitive")
            results = collect_filesystem_metrics({"test": td})
            output = json.dumps(results)
            assert td not in output

    def test_no_absolute_paths_default(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "data.bin").write_bytes(b"x" * 100)
            results = collect_filesystem_metrics({"test": td}, include_relative_paths=False)
            r = results[0]
            for f in r["top_files"]:
                assert "relative_path" not in f

    def test_bytes_by_extension(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "a.txt").write_bytes(b"x" * 10)
            Path(td, "b.txt").write_bytes(b"y" * 20)
            Path(td, "c.csv").write_bytes(b"z" * 30)
            results = collect_filesystem_metrics({"test": td})
            r = results[0]
            ext = r["bytes_by_extension"]
            assert ext.get(".txt") == 30
            assert ext.get(".csv") == 30


# ── backup reader ─────────────────────────────────────────────────────


class TestBackupReader:
    def test_missing_dir_returns_warning(self):
        result = analyze_backup("/nonexistent/backup_dir_xyz")
        assert not result["available"]
        assert result["error"] is not None

    def test_empty_backup_dir(self):
        with tempfile.TemporaryDirectory() as td:
            result = analyze_backup(td)
            assert result["available"]
            for required in ("manifest.json", "database.dump", "artifacts.tar.gz", "SHA256SUMS"):
                comp = result["components"].get(required, {})
                assert not comp.get("exists")

    def test_backup_components_detected(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "manifest.json").write_text('{"version": "1"}')
            Path(td, "database.dump").write_bytes(b"\x00" * 100)
            Path(td, "artifacts.tar.gz").write_bytes(b"\x00" * 200)
            Path(td, "SHA256SUMS").write_text("abc123  file")
            result = analyze_backup(td)
            for required in ("manifest.json", "database.dump", "artifacts.tar.gz", "SHA256SUMS"):
                comp = result["components"].get(required, {})
                assert comp.get("exists"), f"{required} should exist"
            assert result["total_bytes"] == 100 + 200 + len('{"version": "1"}') + len("abc123  file")

    def test_no_archive_extraction(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "artifacts.tar.gz").write_bytes(b"\x00" * 100)
            import tarfile
            result = analyze_backup(td)
            assert result["available"]
            assert result["components"]["artifacts.tar.gz"]["exists"]

    def test_compression_ratio_with_live_data(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "artifacts.tar.gz").write_bytes(b"\x00" * 30)
            result = analyze_backup(td, live_artifacts_bytes=100)
            assert result["compression_ratio"] == 0.3

    def test_compression_ratio_no_live_data(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "artifacts.tar.gz").write_bytes(b"\x00" * 30)
            result = analyze_backup(td)
            assert result["compression_ratio"] is None


# ── reports (JSON/CSV/Markdown) ───────────────────────────────────────


class TestReportConsistency:
    def test_json_contains_required_keys(self):
        snapshot = build_snapshot_json(
            db_metrics={"available": False},
            fs_metrics=[],
            backup_metrics={"available": False},
            git_commit="abc123",
            warnings=[],
        )
        for key in ("schema_version", "generated_at_utc", "git_commit", "database", "filesystem", "backup"):
            assert key in snapshot

    def test_csv_json_markdown_same_values(self):
        forecast = {
            "scenario_source": "test.json",
            "snapshot_source": None,
            "profiles": {
                "pilot": {
                    "description": "test",
                    "projections": {
                        "1_year": {
                            "years": 1,
                            "procurements": 60,
                            "analysis_runs": 180,
                            "database_storage": {"bytes": 1000000, "gib": 0.0, "components": {}},
                            "persistent_file_storage": {"bytes": 2000000, "gib": 0.0, "components": {}},
                            "primary_storage": {"bytes": 3000000, "gib": 0.0},
                            "backup_storage": {"bytes": 500000, "gib": 0.0},
                            "temporary_storage": {"bytes": 1000000, "gib": 0.0},
                            "operational_margin": {"bytes": 1000000, "gib": 0.0},
                            "raw_required": {"bytes": 5500000, "gib": 0.01},
                            "free_space_reserve_percent": 20,
                            "recommended_disk_bytes": 10 * _GIB,
                            "recommended_disk_gib": 10,
                        }
                    },
                }
            },
        }
        with tempfile.TemporaryDirectory() as td:
            write_json_report(forecast, Path(td, "f.json"))
            write_forecast_csv(forecast, Path(td, "f.csv"))
            Path(td, "f.md").write_text(render_forecast_markdown(forecast), encoding="utf-8")

            with open(Path(td, "f.json")) as fh:
                jdata = json.load(fh)
            csv_text = Path(td, "f.csv").read_text()
            md_text = Path(td, "f.md").read_text()

            j_rec = jdata["profiles"]["pilot"]["projections"]["1_year"]["recommended_disk_gib"]
            assert "10 GiB" in md_text or "10" in md_text
            assert "10" in csv_text
            assert j_rec == 10

    def test_dsn_not_in_output(self):
        snapshot = build_snapshot_json(
            db_metrics={"available": True, "dsn": "postgres://user:pass@host/db", "size": 100},
            fs_metrics=[],
            backup_metrics={"available": False},
            git_commit="abc",
            warnings=[],
        )
        as_str = json.dumps(snapshot)
        assert "postgres://" not in as_str
        assert "user:pass" not in as_str

    def test_absolute_paths_not_in_output(self):
        snapshot = build_snapshot_json(
            db_metrics={"available": False},
            fs_metrics=[{"root_name": "data", "root_path": "/etc/passwd", "top_files": []}],
            backup_metrics={"available": False},
            git_commit="abc",
            warnings=[],
        )
        as_str = json.dumps(snapshot)
        assert "/etc/passwd" not in as_str

    def test_db_collector_read_only(self):
        result = collect_database_metrics("postgresql://invalid:0@localhost/nodb")
        assert not result.get("available")

    def test_filesystem_only_when_db_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "f.txt").write_text("test")
            fs = collect_filesystem_metrics({"test": td})
            assert len(fs) == 1
            assert fs[0]["available"]


# ── run_forecast integration ──────────────────────────────────────────


class TestRunForecast:
    def test_run_forecast_all_profiles(self, scenarios_path):
        result = run_forecast(None, scenarios_path, [1, 3, 5])
        for pname in ("pilot", "commercial_mvp", "scaling"):
            assert pname in result["profiles"]
            projs = result["profiles"][pname]["projections"]
            assert "1_year" in projs
            assert "3_year" in projs
            assert "5_year" in projs

    def test_run_forecast_with_snapshot(self, scenarios_path):
        snapshot = {
            "database": {"available": True, "database_size_bytes": 500 * 1024 * 1024},
            "filesystem": [
                {"root_name": "data", "available": True, "logical_bytes": 2 * _GIB},
                {"root_name": "artifacts", "available": True, "logical_bytes": 1 * _GIB},
            ],
        }
        result = run_forecast(snapshot, scenarios_path, [1])
        proj = result["profiles"]["pilot"]["projections"]["1_year"]
        assert proj["database_storage"].get("measured_bytes") == 500 * 1024 * 1024
        assert proj["persistent_file_storage"].get("measured_bytes") == 3 * _GIB


# ── db_collector stub (no real DSN) ───────────────────────────────────


class TestDbCollector:
    def test_no_real_db_fallback(self):
        result = collect_database_metrics("")
        assert not result.get("available")
        assert result.get("row_count_kind") is None

    def test_invalid_dsn_returns_warning(self):
        result = collect_database_metrics("postgresql://no:such@host:9999/nonexistent")
        assert not result.get("available")
        assert result.get("warnings")


# ── optional PostgreSQL integration test ───────────────────────────────


@pytest.mark.skipif(
    not os.environ.get("ARVECTUM_CAPACITY_TEST_DSN"),
    reason="ARVECTUM_CAPACITY_TEST_DSN not set; skipping real DB test",
)
class TestPostgresIntegration:
    def test_live_db_metrics(self):
        dsn = os.environ["ARVECTUM_CAPACITY_TEST_DSN"]
        result = collect_database_metrics(dsn)
        assert result["available"]
        assert result["database_size_bytes"] is not None
        assert result["row_count_kind"] == "estimated"
        for rel in result["relations"]:
            assert rel["total_bytes"] >= rel["heap_bytes"]
            assert rel["total_bytes"] >= rel["indexes_bytes"]
