import json
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def load_aggregate():
    return json.loads((SAMPLES / "capacity" / "public-r3-calibration.aggregate.json").read_text())


class TestAggregateSchema:
    def test_top_level_keys(self):
        agg = load_aggregate()
        required = {"measurement_id", "description", "cohort", "baseline",
                     "final_state", "overall_aggregate", "group_aggregates",
                     "compression_ratios"}
        assert required.issubset(set(agg.keys())), f"Missing keys: {required - set(agg.keys())}"

    def test_cohort_keys(self):
        agg = load_aggregate()
        c = agg["cohort"]
        for k in ("version", "total_cases", "tertile_groups", "scenario"):
            assert k in c, f"Missing cohort.{k}"

    def test_tertile_groups(self):
        agg = load_aggregate()
        groups = agg["cohort"]["tertile_groups"]
        assert set(groups.keys()) == {"lower", "middle", "upper"}
        for g, count in groups.items():
            assert count == 6, f"Group {g} should have 6 cases, got {count}"

    def test_overall_percentile_structure(self):
        agg = load_aggregate()
        for metric_name, metric in agg["overall_aggregate"].items():
            for pk in ("min", "p25", "p50", "p75", "max", "count", "sum", "mean"):
                assert pk in metric, f"overall.{metric_name} missing {pk}"

    def test_group_keys_match_overall(self):
        agg = load_aggregate()
        overall_keys = set(agg["overall_aggregate"].keys())
        for g_name, g_data in agg["group_aggregates"].items():
            g_keys = set(g_data.keys())
            assert g_keys.issubset(overall_keys), \
                f"Group {g_name} has extra keys: {g_keys - overall_keys}"

    def test_baseline_and_final_state(self):
        agg = load_aggregate()
        for k in ("postgresql_database_bytes_baseline", "filesystem_data_bytes_baseline"):
            assert k in agg["baseline"], f"Missing baseline.{k}"
        for k in ("postgresql_database_bytes", "unique_live_source_bytes"):
            assert k in agg["final_state"], f"Missing final_state.{k}"

    def test_compression_ratios(self):
        agg = load_aggregate()
        for k in ("observed_backup_ratio", "forecast_compression_ratio", "metadata_overhead_ratio"):
            assert k in agg["compression_ratios"], f"Missing compression_ratios.{k}"
            assert isinstance(agg["compression_ratios"][k], (int, float)), \
                f"compression_ratios.{k} should be numeric"
