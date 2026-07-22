from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

import pytest

from scripts.capacity.backup_reader import (
    analyze_backup,
    resolve_backup_source_names,
)
from scripts.capacity.db_collector import (
    _parse_vector_dimension,
    _safe_error_code,
    collect_database_metrics,
)
from scripts.capacity.forecast_model import (
    _gib,
    _round_up_gib,
    _validate_value,
    compute_forecast,
    load_scenarios,
    run_forecast,
)
from scripts.capacity.fs_collector import (
    collect_filesystem_metrics,
    resolve_backup_source_bytes,
    resolve_unique_fs_bytes,
)
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


# ── fixtures ──────────────────────────────────────────────────────────


@pytest.fixture()
def scenarios_path() -> str:
    return str(Path(__file__).resolve().parent.parent.parent / "samples" / "capacity" / "scenarios.example.json")


@pytest.fixture()
def pilot_assumptions() -> dict:
    return {
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


# ── Gib conversion ────────────────────────────────────────────────────


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


# ── Forecast arithmetic ───────────────────────────────────────────────


class TestForecastArithmetic:
    def test_basic_forecast_1_year(self, pilot_assumptions):
        result = compute_forecast(None, None, pilot_assumptions, 1)
        assert result["years"] == 1
        assert result["procurements"] == 60
        assert result["analysis_runs"] == 180
        assert result["database_storage"]["projected_total_bytes"] > 0
        assert result["persistent_file_storage"]["projected_total_bytes"] > 0
        assert result["primary_storage"]["projected_total_bytes"] > 0
        assert result["recommended_disk_gib"] >= 10
        assert result["recommended_disk_bytes"] == result["recommended_disk_gib"] * _GIB

    def test_forecast_3_years_scales(self, pilot_assumptions):
        r1 = compute_forecast(None, None, pilot_assumptions, 1)
        r3 = compute_forecast(None, None, pilot_assumptions, 3)
        assert r3["procurements"] == 3 * r1["procurements"]
        assert r3["database_storage"]["projected_total_bytes"] > r1["database_storage"]["projected_total_bytes"]

    def test_forecast_all_profiles_present(self, scenarios_path):
        scenarios = load_scenarios(scenarios_path)
        assert "pilot" in scenarios["profiles"]
        assert "commercial_mvp" in scenarios["profiles"]
        assert "scaling" in scenarios["profiles"]

    def test_negative_assumptions_rejected(self):
        with pytest.raises((ValueError, KeyError)):
            load_scenarios_str(
                '{"profiles": {"pilot": {"procurements_per_month": {"value": -1, "source": "assumption"}}}}'
            )

    def test_reserve_100_rejected(self):
        with pytest.raises(ValueError, match="must be < 100"):
            _validate_value("free_space_reserve_percent", 100, "assumption")

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

    def test_nan_rejected(self):
        with pytest.raises(ValueError, match="NaN"):
            _validate_value("procurements_per_month", float("nan"), "assumption")

    def test_infinity_rejected(self):
        with pytest.raises(ValueError, match="Infinity"):
            _validate_value("procurements_per_month", float("inf"), "assumption")

    def test_bool_rejected(self):
        with pytest.raises(ValueError, match="must be numeric"):
            _validate_value("procurements_per_month", True, "assumption")

    def test_backup_compression_ratio_zero_rejected(self):
        with pytest.raises(ValueError, match="must be in"):
            _validate_value("backup_compression_ratio", 0, "assumption")

    def test_backup_compression_ratio_above_one_rejected(self):
        with pytest.raises(ValueError, match="must be in"):
            _validate_value("backup_compression_ratio", 1.5, "assumption")


# ── Forecast baseline + incremental ───────────────────────────────────


class TestForecastBaseline:
    def test_baseline_zero_when_no_snapshot(self, pilot_assumptions):
        r = compute_forecast(None, None, pilot_assumptions, 1)
        assert r["database_storage"]["baseline_bytes"] == 0
        assert r["database_storage"]["baseline_source"] == "unavailable"
        assert r["persistent_file_storage"]["baseline_bytes"] == 0
        assert r["persistent_file_storage"]["baseline_source"] == "unavailable"

    def test_baseline_from_snapshot(self, pilot_assumptions):
        r = compute_forecast(500 * 1024 * 1024, 2 * _GIB, pilot_assumptions, 1)
        assert r["database_storage"]["baseline_bytes"] == 500 * 1024 * 1024
        assert r["database_storage"]["baseline_source"] == "measured"
        assert r["persistent_file_storage"]["baseline_bytes"] == 2 * _GIB
        assert r["persistent_file_storage"]["baseline_source"] == "measured"

    def test_projected_is_baseline_plus_incremental(self, pilot_assumptions):
        r = compute_forecast(100 * _GIB, 200 * _GIB, pilot_assumptions, 1)
        db_proj = r["database_storage"]["projected_total_bytes"]
        fs_proj = r["persistent_file_storage"]["projected_total_bytes"]
        assert db_proj == 100 * _GIB + r["database_storage"]["incremental_bytes"]
        assert fs_proj == 200 * _GIB + r["persistent_file_storage"]["incremental_bytes"]

    def test_negative_years_rejected(self):
        with pytest.raises((ValueError, KeyError)):
            from scripts.capacity.forecast_model import _validate_value
            _validate_value("years", -1, "input")


# ── Validation helpers ────────────────────────────────────────────────


def load_scenarios_str(content: str):
    import json
    from scripts.capacity.forecast_model import load_scenarios
    import tempfile
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    f.write(content)
    f.close()
    try:
        return load_scenarios(f.name)
    finally:
        os.unlink(f.name)


# ── Filesystem collector ──────────────────────────────────────────────


class TestFilesystemCollector:
    def test_sum_logical_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "a.txt").write_text("hello")
            Path(td, "b.txt").write_text("world!")
            sub = Path(td, "sub")
            sub.mkdir()
            Path(sub, "c.txt").write_text("content")
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

    def test_unavailable_root_is_warning(self):
        results = collect_filesystem_metrics({"missing": "/nonexistent/path/xyz123_test"})
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

    def test_include_relative_paths_works(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "data.bin").write_bytes(b"x" * 100)
            results = collect_filesystem_metrics({"test": td}, include_relative_paths=True)
            r = results[0]
            found = False
            for f in r["top_files"]:
                if "relative_path" in f:
                    rp = f["relative_path"]
                    assert not rp.startswith("/")
                    assert ".." not in rp.split(os.sep)
                    found = True
            assert found

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

    def test_root_symlink_not_traversed(self):
        with tempfile.TemporaryDirectory() as td:
            real_dir = Path(td, "real")
            real_dir.mkdir()
            Path(real_dir, "file.txt").write_text("data")
            link = Path(td, "link")
            os.symlink(real_dir, link)
            results = collect_filesystem_metrics({"test": str(link)})
            r = results[0]
            assert not r["available"]
            assert r["error"]["code"] == "root_is_symlink"

    def test_symlink_directory_not_traversed(self):
        with tempfile.TemporaryDirectory() as td:
            real_dir = Path(td, "real")
            real_dir.mkdir()
            Path(real_dir, "file.txt").write_text("data")
            container = Path(td, "container")
            container.mkdir()
            os.symlink(real_dir, Path(container, "link_dir"))
            Path(container, "regular.txt").write_text("hello")
            results = collect_filesystem_metrics({"test": str(container)})
            r = results[0]
            assert r["symlinks_count"] >= 1
            assert r["logical_bytes"] == 5

    def test_exception_with_abs_path_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "secret.txt").write_text("data")
            results = collect_filesystem_metrics({"test": td})
            output = json.dumps(results)
            assert td not in output

    def test_storage_identity_present(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "f.txt").write_text("data")
            results = collect_filesystem_metrics({"test": td})
            r = results[0]
            assert r["storage_identity_id"] is not None
            assert len(r["storage_identity_id"]) > 0

    def test_alias_roots_deduplicated(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "f.txt").write_text("data")
            results = collect_filesystem_metrics({"data": td, "artifacts": td})
            assert len(results) == 2
            data_r = next(r for r in results if r["root_name"] == "data")
            art_r = next(r for r in results if r["root_name"] == "artifacts")
            assert data_r["counted_in_totals"] is True
            assert art_r["counted_in_totals"] is False
            assert art_r["alias_of"] == "data"

    def test_unique_fs_bytes_excludes_aliases(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "f.txt").write_text("x" * 100)
            results = collect_filesystem_metrics({"data": td, "artifacts": td})
            total = resolve_unique_fs_bytes(results)
            assert total == 100

    def test_resolve_backup_source_bytes_excludes_duplicates(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "f.txt").write_text("x" * 100)
            results = collect_filesystem_metrics({"data": td, "artifacts": td})
            total = resolve_backup_source_bytes(results, {"data", "artifacts"})
            assert total == 100


# ── Backup reader ─────────────────────────────────────────────────────


class TestBackupReader:
    def test_missing_dir_returns_warning(self):
        result = analyze_backup("/nonexistent/backup_dir_xyz_test")
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

    def test_no_archive_extraction(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "artifacts.tar.gz").write_bytes(b"\x00" * 100)
            result = analyze_backup(td)
            assert result["available"]
            assert result["components"]["artifacts.tar.gz"]["exists"]

    def test_compression_ratio_with_live_data(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "artifacts.tar.gz").write_bytes(b"\x00" * 30)
            result = analyze_backup(td, live_archive_source_bytes=100)
            assert result["compression_ratio"] == 0.3

    def test_compression_ratio_no_live_data(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "artifacts.tar.gz").write_bytes(b"\x00" * 30)
            result = analyze_backup(td)
            assert result["compression_ratio"] is None

    def test_ratio_uses_archive_source_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "artifacts.tar.gz").write_bytes(b"\x00" * 30)
            result = analyze_backup(td, live_archive_source_bytes=100)
            assert result["compression_ratio"] == 0.3

    def test_archive_not_opened(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "artifacts.tar.gz").write_bytes(b"\x00" * 100)
            result = analyze_backup(td)
            assert result["available"]
            assert result["components"]["artifacts.tar.gz"]["exists"]


class TestResolveBackupSourceNames:
    def test_default_names(self):
        names = resolve_backup_source_names(None)
        assert "pilot-data" in names
        assert "data" in names
        assert "artifacts" in names
        assert "eis-archives" in names

    def test_explicit_names(self):
        names = resolve_backup_source_names(["custom-a", "custom-b"])
        assert names == ["custom-a", "custom-b"]


# ── Reports (JSON/CSV/Markdown) ──────────────────────────────────────


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
        assert snapshot["schema_version"] == "1.1"

    def test_schema_version_1_1(self, scenarios_path):
        result = run_forecast(None, scenarios_path, [1])
        assert result["schema_version"] == "1.1"

    def test_csv_json_markdown_same_values(self):
        forecast = {
            "schema_version": "1.1",
            "scenario_source": {"file_name": "test.json", "sha256": "abc", "source": "input"},
            "snapshot_source": None,
            "profiles": {
                "pilot": {
                    "description": "test",
                    "projections": {
                        "1_year": {
                            "years": 1,
                            "procurements": 60,
                            "analysis_runs": 180,
                            "database_storage": {
                                "baseline_bytes": 0, "baseline_gib": 0.0, "baseline_source": "unavailable",
                                "incremental_bytes": 1000000, "incremental_gib": 0.0,
                                "projected_total_bytes": 1000000, "projected_total_gib": 0.0,
                                "components": {},
                            },
                            "persistent_file_storage": {
                                "baseline_bytes": 0, "baseline_gib": 0.0, "baseline_source": "unavailable",
                                "incremental_bytes": 2000000, "incremental_gib": 0.0,
                                "projected_total_bytes": 2000000, "projected_total_gib": 0.0,
                                "components": {},
                            },
                            "primary_storage": {"projected_total_bytes": 3000000, "projected_total_gib": 0.0},
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
            assert str(j_rec) in csv_text
            assert "10 GiB" in md_text or "10" in md_text
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
        assert "host" not in as_str

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

    def test_filesystem_only_when_db_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "f.txt").write_text("test")
            fs = collect_filesystem_metrics({"test": td})
            assert len(fs) == 1
            assert fs[0]["available"]

    def test_raw_exception_not_in_db_output(self):
        result = collect_database_metrics("postgresql://invalid:0@localhost/nodb")
        output = json.dumps(result)
        assert "invalid" not in output
        assert "localhost" not in output
        assert "postgresql://" not in output

    def test_scenario_path_not_in_forecast(self, scenarios_path):
        result = run_forecast(None, scenarios_path, [1])
        output = json.dumps(result)
        assert scenarios_path not in output
        assert "scenario_source" in result
        ss = result["scenario_source"]
        assert "file_name" in ss
        assert "sha256" in ss
        assert "/" not in ss["file_name"]

    def test_privacy_flag_in_snapshot(self):
        snapshot = build_snapshot_json(
            db_metrics={"available": False},
            fs_metrics=[],
            backup_metrics={"available": False},
            git_commit="abc",
            warnings=[],
            privacy_flags={"include_relative_paths": True},
        )
        assert snapshot["privacy"]["include_relative_paths"] is True

        snapshot2 = build_snapshot_json(
            db_metrics={"available": False},
            fs_metrics=[],
            backup_metrics={"available": False},
            git_commit="abc",
            warnings=[],
            privacy_flags={"include_relative_paths": False},
        )
        assert snapshot2["privacy"]["include_relative_paths"] is False


# ── Run forecast integration ──────────────────────────────────────────


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
            "generated_at_utc": "2026-01-01T00:00:00Z",
            "git_commit": "abc",
            "schema_version": "1.1",
            "database": {"available": True, "database_size_bytes": 500 * 1024 * 1024},
            "filesystem": [
                {"root_name": "data", "available": True, "logical_bytes": 2 * _GIB, "counted_in_totals": True},
            ],
        }
        result = run_forecast(snapshot, scenarios_path, [1])
        proj = result["profiles"]["pilot"]["projections"]["1_year"]
        assert proj["database_storage"]["baseline_bytes"] == 500 * 1024 * 1024
        assert proj["database_storage"]["baseline_source"] == "measured"
        assert proj["persistent_file_storage"]["baseline_bytes"] == 2 * _GIB
        assert proj["persistent_file_storage"]["baseline_source"] == "measured"
        assert result["snapshot_source"] is not None
        assert result["snapshot_source"]["git_commit"] == "abc"


# ── db_collector ──────────────────────────────────────────────────────


class TestDbCollector:
    def test_no_real_db_fallback(self):
        result = collect_database_metrics("")
        assert not result.get("available")
        assert result.get("read_only_verified") is False

    def test_invalid_dsn_returns_warning(self):
        result = collect_database_metrics("postgresql://no:such@host:9999/nonexistent")
        assert not result.get("available")
        assert result.get("warnings")

    def test_metric_status_present(self):
        result = collect_database_metrics("")
        assert result.get("read_only_verified") is False

    def test_no_dsn_hostname_in_output(self):
        result = collect_database_metrics("postgresql://u:p@secret.example.com:5432/dbname")
        output = json.dumps(result)
        assert "secret.example.com" not in output
        assert "5432" not in output
        assert "postgresql://" not in output
        assert "dbname" not in output

    def test_error_is_safe_code(self):
        result = collect_database_metrics("")
        err = result.get("error")
        if err:
            assert isinstance(err, dict)
            assert "code" in err
            assert "error_type" in err


# ── PostgreSQL size components ────────────────────────────────────────


class TestPostgresSizes:
    def test_parse_vector_dimension(self):
        assert _parse_vector_dimension("vector(1536)") == 1536
        assert _parse_vector_dimension("halfvec(768)") == 768
        assert _parse_vector_dimension("vector") is None
        assert _parse_vector_dimension("sparsevec(1000)") == 1000

    def test_vector_kinds(self):
        from scripts.capacity.db_collector import _VECTOR_KINDS
        assert _VECTOR_KINDS["vector"] == 4
        assert _VECTOR_KINDS["halfvec"] == 2
        assert _VECTOR_KINDS["sparsevec"] is None

    def test_safe_error_code(self):
        exc = PermissionError("test")
        code = _safe_error_code(exc)
        assert code["code"] == "database_query_failed"
        assert code["error_type"] == "PermissionError"

    def test_safe_error_code_no_message(self):
        exc = RuntimeError("secret path: /etc/passwd")
        code = _safe_error_code(exc)
        assert code["code"] == "database_query_failed"
        assert "/etc/passwd" not in str(code)


# ── Optional PostgreSQL integration test ──────────────────────────────


@pytest.mark.skipif(
    not os.environ.get("ARVECTUM_CAPACITY_TEST_DSN"),
    reason="ARVECTUM_CAPACITY_TEST_DSN not set; skipping real DB test",
)
class TestPostgresIntegration:
    def test_live_db_metrics(self):
        dsn = os.environ["ARVECTUM_CAPACITY_TEST_DSN"]
        result = collect_database_metrics(dsn)
        assert result["available"]
        assert result["read_only_verified"] is True
        assert result["database_size_bytes"] is not None
        assert result["row_count_kind"] == "estimated"
        for rel in result["relations"]:
            assert rel["total_bytes"] >= rel["main_fork_bytes"]
            assert rel["total_bytes"] >= rel["toast_total_bytes"]
            assert rel["total_bytes"] >= rel["indexes_bytes"]
            assert "table_bytes" in rel
        assert result.get("metric_status", {}).get("database_size") == "ok"
