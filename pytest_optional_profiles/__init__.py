"""Stub for pytest-optional-profiles."""

OPTIONAL_PROFILE_MARKERS = [
    "integration",
    "postgres",
    "network",
    "llama_cpp",
    "live_smoke",
]


def infer_optional_test_markers(nodeid: str, explicit_markers: set[str]) -> set[str]:
    return set()


def profile_skip_reason(optional_markers: set[str], enabled_profiles: dict[str, bool]) -> str | None:
    return None
