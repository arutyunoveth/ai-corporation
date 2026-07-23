import json
from pathlib import Path
from scripts.capacity.calibration.peak_sampler import compute_peak_scenario

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def load_aggregate():
    return json.loads((SAMPLES / "capacity" / "public-r3-calibration.aggregate.json").read_text())


class TestPeakSampler:
    def test_basic_peak_scenario(self):
        agg = load_aggregate()
        scenario = compute_peak_scenario(agg, cases=100000, runs_per_case=3, retention_years=5)
        assert scenario["peak_estimates"]["total_cases"] == 500000
        assert scenario["peak_estimates"]["total_analysis_runs"] == 1500000
        assert scenario["peak_estimates"]["filesystem_storage_bytes"]["total_ingestion"] > 0

    def test_low_volume(self):
        agg = load_aggregate()
        scenario = compute_peak_scenario(agg, cases=10000, runs_per_case=1, retention_years=1)
        assert scenario["peak_estimates"]["total_cases"] == 10000
        assert scenario["peak_estimates"]["total_analysis_runs"] == 10000

    def test_peak_scenario_keys(self):
        agg = load_aggregate()
        scenario = compute_peak_scenario(agg, cases=50000, runs_per_case=3, retention_years=3)
        required = {"description", "derived_from", "assumptions", "peak_estimates"}
        assert required.issubset(set(scenario.keys()))
