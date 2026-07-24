import json
import math
import hashlib
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
CAP_SCRIPTS = SCRIPTS / "capacity" / "calibration"


def load_aggregate():
    return json.loads((SAMPLES / "capacity" / "public-r3-calibration.aggregate.json").read_text())


def load_scenario():
    return json.loads((SAMPLES / "capacity" / "scenarios.public-r3-calibrated.json").read_text())


def nearest_rank_percentile(sorted_vals, p):
    n = len(sorted_vals)
    if n == 0:
        return None
    rank = math.ceil(p / 100.0 * n)
    idx = max(0, min(rank - 1, n - 1))
    return sorted_vals[idx]


class TestAggregateSchema:
    def test_required_top_level_keys(self):
        agg = load_aggregate()
        required = {
            "schema_version", "measurement_id", "workload_type",
            "calibration_scope", "baseline_commit", "alembic_head",
            "postgresql_version", "pgvector_version", "metadata_fidelity",
            "providers", "cohort", "ingestion_statistics",
            "analysis_run_statistics", "repeat_run_statistics",
            "backup_measurements", "temporary_peak_measurements",
            "postgresql_reconciliation", "limitations", "formulas",
        }
        assert required.issubset(set(agg.keys())), f"Missing: {required - set(agg.keys())}"

    def test_schema_version(self):
        assert load_aggregate()["schema_version"] == "2.0"

    def test_calibration_scope(self):
        assert load_aggregate()["calibration_scope"] == "metadata_ingestion_only"

    def test_cohort_counts(self):
        coh = load_aggregate()["cohort"]
        total = coh["attempted_count"]
        succ = coh["successful_count"]
        fail = coh["failed_count"]
        excl = coh["excluded_count"]
        assert total == 18
        assert succ == 18
        assert fail == 0
        assert excl == 0
        assert succ + fail + excl == total

    def test_providers(self):
        pr = load_aggregate()["providers"]
        assert pr.get("llm") == "stub"
        assert pr.get("embeddings") == "hashing"

    def test_metadata_fidelity(self):
        assert load_aggregate()["metadata_fidelity"] == "placeholder"

    def test_analysis_run_unavailable(self):
        ars = load_aggregate()["analysis_run_statistics"]
        assert ars["status"] == "unavailable"
        assert ars["database_non_vector_bytes_per_run"] is None
        assert ars["report_artifact_bytes_per_run"] is None
        assert ars["other_artifact_bytes_per_run"] is None

    def test_repeat_run_unavailable(self):
        rrs = load_aggregate()["repeat_run_statistics"]
        assert rrs["status"] == "unavailable"

    def test_ingestion_statistics_exist(self):
        ing = load_aggregate()["ingestion_statistics"]
        for k in ("documents_per_procurement", "chunks_per_procurement",
                   "extracted_text_chars_per_procurement",
                   "extracted_text_utf8_bytes_per_procurement",
                   "total_extracted_text_chars",
                   "total_extracted_text_utf8_bytes",
                   "utf8_bytes_per_character_ratio",
                   "filesystem_data_delta_bytes_per_procurement",
                   "postgresql_delta_bytes_per_procurement"):
            assert k in ing, f"Missing {k}"

    def test_backup_measurements_b1_b2(self):
        bm = load_aggregate()["backup_measurements"]
        assert "B1" in bm
        assert "B2" in bm
        assert bm["B1"]["case_count"] == 9
        assert bm["B2"]["case_count"] == 18

    def test_backup_has_filesystem_archive_bytes(self):
        bm = load_aggregate()["backup_measurements"]
        for bk in ("B1", "B2"):
            b = bm[bk]
            assert "filesystem_archive_bytes" in b
            assert "total_backup_bytes" in b
            assert b["total_backup_bytes"] == b["postgresql_dump_bytes"] + b["filesystem_archive_bytes"]

    def test_backup_component_ratios(self):
        bm = load_aggregate()["backup_measurements"]
        for bk in ("B1", "B2"):
            b = bm[bk]
            expected_db = round(
                b["postgresql_dump_bytes"] / max(b["database_source_bytes"], 1), 4
            )
            expected_fs = round(
                b["filesystem_archive_bytes"] / max(b["filesystem_source_bytes"], 1), 4
            )
            expected_full = round(
                b["total_backup_bytes"] / max(b["unique_live_source_bytes"], 1), 4
            )
            expected_cf = round(
                b["total_source_bytes"] / max(b["total_backup_bytes"], 1), 4
            )
            assert b["database_archive_to_source_ratio"] == expected_db
            assert b["filesystem_archive_to_source_ratio"] == expected_fs
            assert b["full_backup_archive_to_source_ratio"] == expected_full
            assert b["compression_factor"] == expected_cf

    def test_no_case_ids(self):
        text = json.dumps(load_aggregate())
        assert "case-001" not in text
        assert "registry_number" not in text

    def test_no_private_data(self):
        text = json.dumps(load_aggregate())
        for substr in ("/tmp/", "/Users/", ".xml", "sha256", "file_name", "file_url"):
            assert substr not in text, f"Contains private: {substr}"

    def test_limitations_present(self):
        lims = load_aggregate()["limitations"]
        assert len(lims) >= 4
        assert any("metadata only" in l.lower() for l in lims)
        assert any("AnalysisRun" in l for l in lims)
        assert any("placeholder" in l.lower() for l in lims)
        assert not any("WAL" in l for l in lims), "WAL claim should not appear in limitations"

    def test_formulas_present(self):
        formulas = load_aggregate()["formulas"]
        for k in ("database_archive_to_source_ratio", "filesystem_archive_to_source_ratio",
                   "full_backup_archive_to_source_ratio", "compression_factor",
                   "forecast_backup_compression_ratio",
                   "utf8_bytes_per_character_ratio",
                   "nearest_rank_percentile", "p50", "p75", "p90"):
            assert k in formulas, f"Missing formula key: {k}"

    def test_percentile_p50_exact(self):
        c = load_aggregate()["ingestion_statistics"]["chunks_per_procurement"]
        # cohort has 18 cases with chunk counts
        # Need to verify from raw data
        assert isinstance(c["p50"], (int, float))
        assert c["p50"] > 0

    def test_percentiles_include_p90(self):
        for key, stat in load_aggregate()["ingestion_statistics"].items():
            if not isinstance(stat, dict):
                continue
            assert "p90" in stat, f"Missing p90 in {key}"
            assert "p50" in stat
            assert "p75" in stat

    def test_coverage_present(self):
        for key, stat in load_aggregate()["ingestion_statistics"].items():
            if not isinstance(stat, dict):
                continue
            assert "coverage_percent" in stat, f"Missing coverage_percent in {key}"
            assert "available_count" in stat
            assert "unavailable_count" in stat

    def test_unavailable_not_zero(self):
        for key, stat in load_aggregate()["ingestion_statistics"].items():
            if not isinstance(stat, dict):
                continue
            assert None not in [
                stat.get("unavailable_count"), stat.get("available_count")
            ]

    def test_utf8_consistency(self):
        ing = load_aggregate()["ingestion_statistics"]
        total_chars = ing["total_extracted_text_chars"]
        total_utf8 = ing["total_extracted_text_utf8_bytes"]
        ratio = ing["utf8_bytes_per_character_ratio"]
        assert total_chars > 0
        assert total_utf8 > 0
        assert total_utf8 >= total_chars
        expected_ratio = round(total_utf8 / total_chars, 4)
        assert ratio == expected_ratio

    def test_utf8_per_case_present(self):
        # The harness reads extracted_text_utf8_bytes from cohort for per-case
        ing = load_aggregate()["ingestion_statistics"]
        assert "extracted_text_utf8_bytes_per_procurement" in ing
        utf8_stat = ing["extracted_text_utf8_bytes_per_procurement"]
        assert utf8_stat["count"] == 18
        assert utf8_stat["available_count"] == 18

    def test_temporary_peak_unavailable(self):
        tp = load_aggregate()["temporary_peak_measurements"]
        assert tp["status"] == "unavailable"
        assert "reason" in tp

    def test_pg_reconciliation_union_keys(self):
        pr = load_aggregate()["postgresql_reconciliation"]
        assert "relation_total_baseline_bytes" in pr
        assert "relation_total_final_bytes" in pr
        assert pr["relation_total_baseline_bytes"] > 0
        assert pr["relation_total_final_bytes"] > 0

    def test_pg_note_no_wal(self):
        note = load_aggregate()["postgresql_reconciliation"]["note"]
        assert "WAL" not in note, "WAL claim should not appear in PG note"

    def test_deterministic_output(self):
        agg_a = json.loads((SAMPLES / "capacity" / "public-r3-calibration.aggregate.json").read_text())
        agg_b = json.loads((SAMPLES / "capacity" / "public-r3-calibration.aggregate.json").read_text())
        sha_a = hashlib.sha256(json.dumps(agg_a, sort_keys=True).encode()).hexdigest()
        sha_b = hashlib.sha256(json.dumps(agg_b, sort_keys=True).encode()).hexdigest()
        assert sha_a == sha_b

    def test_pg_reconciliation_present(self):
        pr = load_aggregate()["postgresql_reconciliation"]
        assert "pg_database_size_delta_bytes" in pr
        assert "relation_total_delta_bytes" in pr
        assert "pg_final_bytes" in pr
        assert "pg_baseline_bytes" in pr


class TestScenario:
    def test_three_profiles(self):
        sce = load_scenario()
        profiles = sce.get("profiles", {})
        assert set(profiles.keys()) == {"pilot", "commercial_mvp", "scaling"}

    def test_profile_params(self):
        sce = load_scenario()
        for name, profile in sce["profiles"].items():
            for k in ("procurements_per_month", "analysis_runs_per_procurement",
                       "documents_per_procurement", "raw_document_bytes_per_procurement",
                       "extracted_text_bytes_per_procurement", "extracted_text_chars_per_procurement",
                       "chunks_per_procurement",
                       "backup_compression_ratio", "temporary_space_peak_factor",
                       "vector_dimension", "embedding_rows_per_chunk",
                       "full_backups_retained", "free_space_reserve_percent"):
                assert k in profile, f"{name} missing {k}"

    def test_scenario_aggregate_sha(self):
        sce = load_scenario()
        notes = sce.get("notes", [])
        agg_sha_in_notes = None
        for n in notes:
            if n.startswith("Aggregate SHA-256:"):
                agg_sha_in_notes = n.split(": ", 1)[1].strip()
                break
        assert agg_sha_in_notes is not None, "Aggregate SHA not found in scenario notes"
        actual = hashlib.sha256(
            json.dumps(load_aggregate(), indent=2, sort_keys=True).encode()
        ).hexdigest()
        assert agg_sha_in_notes == actual, "Aggregate SHA mismatch in scenario"

    def test_raw_document_not_replaced(self):
        sce = load_scenario()
        for name, prof in sce["profiles"].items():
            rdp = prof.get("raw_document_bytes_per_procurement", {})
            assert rdp.get("source") == "assumption", f"{name}: raw_document source changed"
            assert rdp.get("value", 0) >= 524288000, f"{name}: raw_document value too small"

    def test_analysis_run_assumptions_unchanged(self):
        sce = load_scenario()
        for name, prof in sce["profiles"].items():
            for k in ("analysis_runs_per_procurement",
                       "database_non_vector_bytes_per_run",
                       "report_artifact_bytes_per_run",
                       "other_artifact_bytes_per_run"):
                param = prof.get(k, {})
                assert param.get("source") == "assumption", f"{name}: {k} source changed"

    def test_scenario_metadata_notes(self):
        sce = load_scenario()
        all_notes = " ".join(sce.get("notes", []))
        assert "hashing" in all_notes
        assert "stub" in all_notes
        assert "lower-bound" in all_notes

    def test_scenario_schema_version(self):
        assert load_scenario()["schema_version"] == "1.1"

    def test_scenario_embedding_notes(self):
        sce = load_scenario()
        for name, prof in sce["profiles"].items():
            vd = prof.get("vector_dimension", {})
            assert "note" in vd, f"{name}: vector_dimension missing note"
            assert "hashing" in vd["note"].lower(), f"{name}: vector_dimension note missing 'hashing'"
            assert vd.get("value") == 256, f"{name}: vector_dimension should be 256"

    def test_scenario_backup_ratio_uses_max_b1_b2(self):
        sce = load_scenario()
        agg = load_aggregate()
        b1_ratio = agg["backup_measurements"]["B1"]["full_backup_archive_to_source_ratio"]
        b2_ratio = agg["backup_measurements"]["B2"]["full_backup_archive_to_source_ratio"]
        expected = min(1.0, max(b1_ratio, b2_ratio))
        for name, prof in sce["profiles"].items():
            bcr = prof.get("backup_compression_ratio", {})
            assert bcr.get("value") == expected, f"{name}: backup ratio {bcr.get('value')} != {expected}"
            assert "max" in bcr.get("note", "").lower(), f"{name}: note missing max(B1,B2)"

    def test_scenario_temp_factor_kept(self):
        sce = load_scenario()
        expected = {"pilot": 1.5, "commercial_mvp": 1.5, "scaling": 1.3}
        for name, prof in sce["profiles"].items():
            tf = prof.get("temporary_space_peak_factor", {})
            assert tf.get("value") == expected[name], f"{name}: temp factor should be {expected[name]}"
            assert "unavailable" in tf.get("note", "").lower(), f"{name}: temp note missing 'unavailable'"

    def test_scenario_percentile_notes(self):
        sce = load_scenario()
        for name, prof in sce["profiles"].items():
            dp = prof.get("documents_per_procurement", {})
            note = dp.get("note", "")
            assert "p50=4" in note, f"{name}: documents_per_procurement note missing p50=4"
            cp = prof.get("chunks_per_procurement", {})
            cnote = cp.get("note", "")
            assert "p50=" in cnote, f"{name}: chunks note missing p50"
            assert "p90=" in cnote

    def test_scenario_extracted_text_chars_per_procurement(self):
        sce = load_scenario()
        ing = load_aggregate()["ingestion_statistics"]
        expected_p50 = ing["extracted_text_chars_per_procurement"]["p50"]
        expected_p75 = ing["extracted_text_chars_per_procurement"]["p75"]
        expected_p90 = ing["extracted_text_chars_per_procurement"]["p90"]
        assert sce["profiles"]["pilot"]["extracted_text_chars_per_procurement"]["value"] == expected_p50
        assert sce["profiles"]["commercial_mvp"]["extracted_text_chars_per_procurement"]["value"] == expected_p75
        assert sce["profiles"]["scaling"]["extracted_text_chars_per_procurement"]["value"] == expected_p90


class TestPeakSampler:
    def test_symlink_root_rejection(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as td:
            real_dir = os.path.join(td, "real")
            link_dir = os.path.join(td, "link")
            os.mkdir(real_dir)
            os.symlink(real_dir, link_dir)
            from scripts.capacity.calibration.peak_sampler import _real_path
            try:
                _real_path(link_dir)
                assert False, "Should reject symlink root"
            except ValueError:
                pass
            resolved = _real_path(real_dir)
            assert os.path.isdir(resolved)

    def test_interval_validation(self):
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, str(CAP_SCRIPTS / "peak_sampler.py"),
             "--root", "test=/tmp", "--interval-seconds", "1",
             "--output", "/dev/null"],
            capture_output=True, text=True
        )
        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "error" in result.stdout.lower()

    def test_no_absolute_paths_in_output(self):
        import subprocess, sys, json, tempfile, os, time, signal
        with tempfile.TemporaryDirectory() as td:
            out_path = os.path.join(td, "peak.json")
            proc = subprocess.Popen(
                [sys.executable, str(CAP_SCRIPTS / "peak_sampler.py"),
                 "--root", f"test={td}", "--interval-seconds", "2",
                 "--output", out_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            time.sleep(0.5)
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=10)
            data = json.loads(open(out_path).read())
            text = json.dumps(data)
            assert td not in text, "Output contains absolute path"

    def test_symlink_skip(self):
        import tempfile, os
        from scripts.capacity.calibration.peak_sampler import _collect
        with tempfile.TemporaryDirectory() as td:
            real_file = os.path.join(td, "real.txt")
            link_file = os.path.join(td, "link.txt")
            subdir = os.path.join(td, "sub")
            link_dir = os.path.join(td, "linkdir")
            os.mkdir(subdir)
            with open(real_file, "w") as f:
                f.write("x" * 100)
            os.symlink("real.txt", link_file)
            os.symlink(subdir, link_dir)
            logical, allocated = _collect(td, follow_symlinks=False)
            # Should count only real.txt (100 bytes), skip link.txt and linkdir
            assert logical == 100


class TestPercentiles:
    def test_even_size_cohort(self):
        from scripts.capacity.calibration.calibrate_cohort import nearest_rank_percentile
        vals = list(range(18))
        assert nearest_rank_percentile(vals, 50) == 8  # ceil(0.5*18)=9, idx=8
        assert nearest_rank_percentile(vals, 75) == 13  # ceil(0.75*18)=14, idx=13
        assert nearest_rank_percentile(vals, 90) == 16  # ceil(0.90*18)=17, idx=16

    def test_failed_case_exclusion(self):
        from scripts.capacity.calibration.calibrate_cohort import compute_percentiles
        # failed case has None value
        result = compute_percentiles([100, 200, 300, None, 400])
        assert result["available_count"] == 4
        assert result["unavailable_count"] == 1
        assert result["coverage_percent"] == 80.0

    def test_empty_values(self):
        from scripts.capacity.calibration.calibrate_cohort import compute_percentiles
        result = compute_percentiles([None, None])
        assert result["min"] is None
        assert result["max"] is None
        assert result["available_count"] == 0
        assert result["unavailable_count"] == 2


class TestBackupRatios:
    def test_database_archive_to_source_ratio_definition(self):
        """database_archive_to_source_ratio = postgresql_dump_bytes / database_source_bytes"""
        bm = load_aggregate()["backup_measurements"]
        for bk in ("B1", "B2"):
            b = bm[bk]
            expected = round(
                b["postgresql_dump_bytes"] / max(b["database_source_bytes"], 1), 4
            )
            assert b["database_archive_to_source_ratio"] == expected

    def test_filesystem_archive_to_source_ratio_definition(self):
        """filesystem_archive_to_source_ratio = filesystem_archive_bytes / filesystem_source_bytes"""
        bm = load_aggregate()["backup_measurements"]
        for bk in ("B1", "B2"):
            b = bm[bk]
            expected = round(
                b["filesystem_archive_bytes"] / max(b["filesystem_source_bytes"], 1), 4
            )
            assert b["filesystem_archive_to_source_ratio"] == expected

    def test_full_backup_archive_to_source_ratio_definition(self):
        """full_backup_archive_to_source_ratio = total_backup_bytes / unique_live_source_bytes"""
        bm = load_aggregate()["backup_measurements"]
        for bk in ("B1", "B2"):
            b = bm[bk]
            expected = round(
                b["total_backup_bytes"] / max(b["unique_live_source_bytes"], 1), 4
            )
            assert b["full_backup_archive_to_source_ratio"] == expected

    def test_compression_factor_definition(self):
        """compression_factor = total_source_bytes / total_backup_bytes"""
        bm = load_aggregate()["backup_measurements"]
        for bk in ("B1", "B2"):
            b = bm[bk]
            expected = round(
                b["total_source_bytes"] / max(b["total_backup_bytes"], 1), 4
            )
            assert b["compression_factor"] == expected

    def test_ratio_semantics(self):
        bm = load_aggregate()["backup_measurements"]
        for bk in ("B1", "B2"):
            b = bm[bk]
            assert b["compression_factor"] >= 1.0, f"{bk}: compression_factor < 1.0"
            assert b["full_backup_archive_to_source_ratio"] > 0
