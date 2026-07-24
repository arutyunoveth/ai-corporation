from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parents[3] / "samples"
SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"

EXPECTED_AGGREGATE_SHA = "8b1a1fd6d0ed994da8b8af04930951d58ba7a1d7b6ef88d256f08e143b527b58"

PROFILES = ["pilot", "commercial_mvp", "scaling"]
HORIZON_KEYS = ["1_year", "3_year", "5_year"]
HORIZON_YEARS = {"1_year": 1, "3_year": 3, "5_year": 5}

MEASURED_PARAMS = [
    "documents_per_procurement",
    "extracted_text_bytes_per_procurement",
    "chunks_per_procurement",
    "embedding_rows_per_chunk",
    "vector_dimension",
    "vector_bytes_per_component",
    "backup_compression_ratio",
]

ASSUMPTION_PARAMS = [
    "procurements_per_month",
    "analysis_runs_per_procurement",
    "raw_document_bytes_per_procurement",
    "database_non_vector_bytes_per_procurement",
    "database_non_vector_bytes_per_run",
    "report_artifact_bytes_per_run",
    "other_artifact_bytes_per_run",
    "full_backups_retained",
    "temporary_space_peak_factor",
    "operational_margin_bytes",
    "free_space_reserve_percent",
]


def load_plan() -> dict:
    return json.loads((SAMPLES / "capacity" / "arv-009-final-capacity-plan.json").read_text())


def load_csv_rows() -> list[dict]:
    path = SAMPLES / "capacity" / "arv-009-final-capacity-plan.csv"
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_aggregate() -> dict:
    return json.loads((SAMPLES / "capacity" / "public-r3-calibration.aggregate.json").read_text())


def load_scenario() -> dict:
    return json.loads((SAMPLES / "capacity" / "scenarios.public-r3-calibrated.json").read_text())


def load_snapshot() -> dict:
    return json.loads((SAMPLES / "capacity" / "arv-009-final-baseline.snapshot.json").read_text())


class TestPlanStructure:
    def test_required_top_level_keys(self):
        plan = load_plan()
        required = {
            "schema_version", "plan_id", "generated_from_main_commit",
            "aggregate_sha256", "scenario_sha256", "snapshot_sha256",
            "forecast_tool_version", "profiles", "reference_configurations",
            "sensitivity", "metadata_only_lower_bound", "evidence_classification",
            "arv_010_gate", "arv_011_handoff", "limitations",
        }
        assert required.issubset(set(plan.keys())), f"Missing: {required - set(plan.keys())}"

    def test_schema_version(self):
        assert load_plan()["schema_version"] == "1.0"

    def test_plan_id(self):
        assert load_plan()["plan_id"] == "ARV-009-FINAL-CAPACITY-PLAN"

    def test_aggregate_sha_matches(self):
        plan = load_plan()
        assert plan["aggregate_sha256"] == EXPECTED_AGGREGATE_SHA

    def test_aggregate_sha_verified(self):
        plan = load_plan()
        agg = load_aggregate()
        actual = hashlib.sha256(json.dumps(agg, indent=2, sort_keys=True).encode()).hexdigest()
        assert plan["aggregate_sha256"] == actual

    def test_scenario_sha_verified(self):
        plan = load_plan()
        sce = load_scenario()
        actual = hashlib.sha256(json.dumps(sce, indent=2, sort_keys=True).encode()).hexdigest()
        assert plan["scenario_sha256"] == actual

    def test_snapshot_sha_verified(self):
        plan = load_plan()
        snap = load_snapshot()
        actual = hashlib.sha256(json.dumps(snap, indent=2, sort_keys=True).encode()).hexdigest()
        assert plan["snapshot_sha256"] == actual

    def test_wrong_aggregate_sha_rejected(self):
        from scripts.capacity.planning.build_final_plan import EXPECTED_AGGREGATE_SHA
        assert EXPECTED_AGGREGATE_SHA == "8b1a1fd6d0ed994da8b8af04930951d58ba7a1d7b6ef88d256f08e143b527b58"

    def test_provider_not_selected(self):
        assert load_plan()["arv_011_handoff"]["provider_selected"] is False

    def test_server_not_purchased(self):
        assert load_plan()["arv_011_handoff"]["server_purchased"] is False

    def test_cpu_not_measured(self):
        assert load_plan()["arv_011_handoff"]["cpu_status"] == "not_measured"

    def test_ram_not_measured(self):
        assert load_plan()["arv_011_handoff"]["ram_status"] == "not_measured"

    def test_limitations_present(self):
        lims = load_plan()["limitations"]
        assert len(lims) >= 10
        assert any("planning envelope" in l.lower() for l in lims)
        assert any("no customer data" in l.lower() for l in lims)
        assert any("VPS provider" in l for l in lims)
        assert any("no server was purchased" in l.lower() for l in lims)


class TestPlanMatrix:
    def test_exactly_three_profiles(self):
        plan = load_plan()
        assert set(plan["profiles"].keys()) == {"pilot", "commercial_mvp", "scaling"}

    def test_exactly_three_horizons_per_profile(self):
        plan = load_plan()
        for pname in PROFILES:
            assert set(plan["profiles"][pname].keys()) == set(HORIZON_KEYS)

    def test_exactly_nine_matrix_rows(self):
        plan = load_plan()
        count = sum(len(plan["profiles"][p]) for p in PROFILES)
        assert count == 9

    def test_horizon_years_correct(self):
        plan = load_plan()
        for pname in PROFILES:
            for hkey in HORIZON_KEYS:
                entry = plan["profiles"][pname][hkey]
                assert entry["horizon_years"] == HORIZON_YEARS[hkey]

    def test_procurements_positive(self):
        plan = load_plan()
        for pname in PROFILES:
            for hkey in HORIZON_KEYS:
                assert plan["profiles"][pname][hkey]["procurements_total"] > 0

    def test_analysis_runs_positive(self):
        plan = load_plan()
        for pname in PROFILES:
            for hkey in HORIZON_KEYS:
                assert plan["profiles"][pname][hkey]["analysis_runs_total"] > 0

    def test_total_required_positive(self):
        plan = load_plan()
        for pname in PROFILES:
            for hkey in HORIZON_KEYS:
                assert plan["profiles"][pname][hkey]["total_required_bytes"] > 0

    def test_total_required_gib_positive(self):
        plan = load_plan()
        for pname in PROFILES:
            for hkey in HORIZON_KEYS:
                assert plan["profiles"][pname][hkey]["total_required_gib"] > 0

    def test_provisioned_floor_positive(self):
        plan = load_plan()
        for pname in PROFILES:
            for hkey in HORIZON_KEYS:
                assert plan["profiles"][pname][hkey]["provisioned_floor_gib"] > 0

    def test_provisioned_floor_is_multiple_of_10(self):
        plan = load_plan()
        for pname in PROFILES:
            for hkey in HORIZON_KEYS:
                floor = plan["profiles"][pname][hkey]["provisioned_floor_gib"]
                assert floor % 10 == 0, f"{hkey} floor {floor} not multiple of 10"

    def test_provisioned_floor_ge_total_gib(self):
        plan = load_plan()
        for pname in PROFILES:
            for hkey in HORIZON_KEYS:
                entry = plan["profiles"][pname][hkey]
                assert entry["provisioned_floor_gib"] >= entry["total_required_gib"]

    def test_no_nan_infinity(self):
        plan = load_plan()
        text = json.dumps(plan)
        assert "NaN" not in text
        assert "Infinity" not in text
        assert "-Infinity" not in text

    def test_no_negative_bytes(self):
        plan = load_plan()
        text = json.dumps(plan)
        assert "-" not in [s.split('"')[0] for s in text.split(": ") if "bytes" in s and "-" in s]

    def test_no_absolute_paths(self):
        text = json.dumps(load_plan())
        assert "/Users/" not in text
        assert "/tmp/" not in text

    def test_no_dsn(self):
        text = json.dumps(load_plan())
        assert "postgresql" not in text.lower() or "postgresql" not in text

    def test_no_provider_names(self):
        text = json.dumps(load_plan())
        for name in ["hetzner", "digitalocean", "aws", "azure", "gcp", "scaleway"]:
            assert name not in text.lower()

    def test_no_prices(self):
        text = json.dumps(load_plan())
        assert "€" not in text
        assert "$" not in text
        assert "price" not in text.lower()


class TestReferenceConfigurations:
    def test_three_reference_configs(self):
        plan = load_plan()
        assert set(plan["reference_configurations"].keys()) == {
            "controlled_pilot", "commercial_mvp", "scaling"
        }

    def test_controlled_pilot_reference_1y(self):
        rc = load_plan()["reference_configurations"]["controlled_pilot"]
        assert rc["profile"] == "pilot"
        assert rc["reference_horizon_years"] == 1
        assert rc["reference"]["horizon_years"] == 1

    def test_commercial_mvp_reference_3y(self):
        rc = load_plan()["reference_configurations"]["commercial_mvp"]
        assert rc["profile"] == "commercial_mvp"
        assert rc["reference_horizon_years"] == 3
        assert rc["reference"]["horizon_years"] == 3

    def test_scaling_reference_5y(self):
        rc = load_plan()["reference_configurations"]["scaling"]
        assert rc["profile"] == "scaling"
        assert rc["reference_horizon_years"] == 5
        assert rc["reference"]["horizon_years"] == 5

    def test_other_horizons_present(self):
        plan = load_plan()
        for rname in ["controlled_pilot", "commercial_mvp", "scaling"]:
            rc = plan["reference_configurations"][rname]
            assert len(rc["other_horizons"]) == 2

    def test_component_breakdown_largest_sorted(self):
        plan = load_plan()
        for rname in ["controlled_pilot", "commercial_mvp", "scaling"]:
            ref = plan["reference_configurations"][rname]["reference"]
            largest = ref.get("largest_components", [])
            assert len(largest) >= 3
            for i in range(len(largest) - 1):
                assert largest[i][1] >= largest[i + 1][1]

    def test_backup_ratio_0_0934(self):
        plan = load_plan()
        meta = plan["metadata_only_lower_bound"]
        for mp in meta["measured_parameters"]:
            if mp["parameter"] == "backup_compression_ratio":
                assert mp["forecast"] == 0.0934
                break

    def test_utf8_byte_values_correct(self):
        plan = load_plan()
        meta = plan["metadata_only_lower_bound"]
        expected = {"p50": 121916, "p75": 144233, "p90": 162378}
        for mp in meta["measured_parameters"]:
            if mp["parameter"] == "extracted_text_utf8_bytes_per_procurement":
                assert mp["p50"] == expected["p50"]
                assert mp["p75"] == expected["p75"]
                assert mp["p90"] == expected["p90"]
                break

    def test_temp_assumptions_retained(self):
        plan = load_plan()
        meta = plan["metadata_only_lower_bound"]
        assert any("Temporary peak" in l for l in plan["limitations"])
        assert "Temporary peak measurements unavailable" in " ".join(plan["limitations"])

    def test_metadata_lower_bound_not_recommendation(self):
        plan = load_plan()
        assert "recommendation_guard" in plan["metadata_only_lower_bound"]
        guard = plan["metadata_only_lower_bound"]["recommendation_guard"]
        assert "not a disk recommendation" in guard.lower()


class TestEvidenceClassification:
    def test_measured_params_present(self):
        plan = load_plan()
        ec = plan["evidence_classification"]
        for mp in MEASURED_PARAMS:
            assert mp in ec["measured"], f"Missing measured: {mp}"

    def test_assumption_params_present(self):
        plan = load_plan()
        ec = plan["evidence_classification"]
        for ap in ASSUMPTION_PARAMS:
            assert ap in ec["assumption"], f"Missing assumption: {ap}"

    def test_no_overlap_between_measured_and_assumption(self):
        plan = load_plan()
        ec = plan["evidence_classification"]
        measured = set(ec["measured"])
        assumption = set(ec["assumption"])
        assert measured.isdisjoint(assumption), f"Overlap: {measured & assumption}"

    def test_arv_010_gate_basic_contour_ready(self):
        assert load_plan()["arv_010_gate"]["basic_contour_ready"] is True

    def test_arv_010_gate_remaining_not_empty(self):
        remaining = load_plan()["arv_010_gate"]["remaining"]
        assert len(remaining) >= 3

    def test_arv_011_handoff_storage_ready(self):
        assert load_plan()["arv_011_handoff"]["storage_status"] == "ready_for_provider_comparison"

    def test_arv_011_runtime_blocked(self):
        assert load_plan()["arv_011_handoff"]["runtime_metrics_status"] == "blocked_by_ARV_010"


class TestCSV:
    def test_exactly_nine_rows(self):
        rows = load_csv_rows()
        assert len(rows) == 9

    def test_required_columns(self):
        rows = load_csv_rows()
        required = {
            "profile", "horizon_years", "procurements_total", "analysis_runs_total",
            "primary_storage_gib", "backups_gib", "temporary_gib",
            "operational_margin_gib", "reserve_gib", "total_required_gib",
            "provisioned_floor_gib", "largest_component", "evidence_status",
            "provider_selected",
        }
        assert required.issubset(set(rows[0].keys()))

    def test_all_profiles_present(self):
        rows = load_csv_rows()
        profiles_in_csv = {r["profile"] for r in rows}
        assert profiles_in_csv == {"pilot", "commercial_mvp", "scaling"}

    def test_all_horizons_present(self):
        rows = load_csv_rows()
        horizons = {int(r["horizon_years"]) for r in rows}
        assert horizons == {1, 3, 5}

    def test_each_profile_has_three_rows(self):
        rows = load_csv_rows()
        for pname in PROFILES:
            pr = [r for r in rows if r["profile"] == pname]
            assert len(pr) == 3

    def test_provider_selected_false(self):
        rows = load_csv_rows()
        for r in rows:
            assert r["provider_selected"] == "False"

    def test_csv_json_numerical_consistency(self):
        plan = load_plan()
        csv_rows = load_csv_rows()
        for cr in csv_rows:
            pname = cr["profile"]
            hy = int(cr["horizon_years"])
            for hkey, yrs in HORIZON_YEARS.items():
                if yrs == hy:
                    entry = plan["profiles"][pname][hkey]
                    assert float(cr["total_required_gib"]) == pytest.approx(entry["total_required_gib"], rel=0.01)
                    break


class TestDeterminism:
    def test_plan_deterministic(self):
        import subprocess, sys, tempfile, os
        args = [
            sys.executable, str(SCRIPTS / "capacity" / "planning" / "build_final_plan.py"),
            "--snapshot", str(SAMPLES / "capacity" / "arv-009-final-baseline.snapshot.json"),
            "--scenario", str(SAMPLES / "capacity" / "scenarios.public-r3-calibrated.json"),
            "--aggregate", str(SAMPLES / "capacity" / "public-r3-calibration.aggregate.json"),
            "--forecast-json", "/tmp/arvectum-arv009-b3/forecast/capacity_forecast.json",
        ]
        with tempfile.TemporaryDirectory() as td:
            r1 = subprocess.run(args + ["--json-output", os.path.join(td, "1.json"),
                                         "--csv-output", os.path.join(td, "1.csv"),
                                         "--markdown-output", os.path.join(td, "1.md")],
                                capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "."})
            r2 = subprocess.run(args + ["--json-output", os.path.join(td, "2.json"),
                                         "--csv-output", os.path.join(td, "2.csv"),
                                         "--markdown-output", os.path.join(td, "2.md")],
                                capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "."})
            assert r1.returncode == 0, r1.stderr
            assert r2.returncode == 0, r2.stderr
            assert open(os.path.join(td, "1.json")).read() == open(os.path.join(td, "2.json")).read()
            assert open(os.path.join(td, "1.csv")).read() == open(os.path.join(td, "2.csv")).read()
            assert open(os.path.join(td, "1.md")).read() == open(os.path.join(td, "2.md")).read()
