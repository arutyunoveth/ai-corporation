"""Generic validation helpers for operator case-set reruns."""
from __future__ import annotations

from collections.abc import Iterable


def compare_case_ids(expected: Iterable[str], observed: Iterable[str]) -> dict[str, object]:
    expected_set = {str(value).strip() for value in expected if str(value).strip()}
    observed_set = {str(value).strip() for value in observed if str(value).strip()}
    missing = sorted(expected_set - observed_set)
    unexpected = sorted(observed_set - expected_set)
    return {
        "expected": sorted(expected_set),
        "observed": sorted(observed_set),
        "missing": missing,
        "unexpected": unexpected,
        "is_match": not missing and not unexpected,
    }
