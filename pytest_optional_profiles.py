from __future__ import annotations

from pathlib import Path

OPTIONAL_PROFILE_OPTIONS = {
    "integration": "--run-integration",
    "postgres": "--run-postgres",
    "network": "--run-network",
    "llama_cpp": "--run-llama-cpp",
    "live_smoke": "--run-live-smoke",
}

OPTIONAL_PROFILE_MARKERS = tuple(OPTIONAL_PROFILE_OPTIONS)
_PROFILE_PRIORITY = ("live_smoke", "postgres", "llama_cpp", "network", "integration")
_LLAMA_CPP_TEST_FILES = {
    "test_rag_embedding_server_cli.py",
    "test_rag_llama_cpp_embeddings.py",
    "test_rag_model_selection.py",
}
_LIVE_SMOKE_TEST_FILES = {
    "test_tender_operator_agent_demo_acceptance_smoke.py",
    "test_tender_operator_agent_getdocs_ip_client.py",
    "test_tender_operator_agent_zakupki_soap_client.py",
}


def infer_optional_test_markers(nodeid: str, own_markers: set[str] | None = None) -> set[str]:
    normalized_nodeid = nodeid.lower()
    file_name = Path(normalized_nodeid.split("::", 1)[0]).name
    test_name = normalized_nodeid.rsplit("::", 1)[-1]
    explicit = {marker.lower() for marker in (own_markers or set()) if marker.lower() in OPTIONAL_PROFILE_OPTIONS}
    inferred = set(explicit)

    if "postgres" in explicit or file_name == "test_postgres_pgvector_integration.py":
        inferred.add("postgres")
    elif file_name.endswith("_integration.py"):
        inferred.add("integration")

    if file_name in _LLAMA_CPP_TEST_FILES and "llama_cpp" in test_name:
        inferred.add("llama_cpp")

    if _is_live_smoke_test(test_name, file_name):
        inferred.update({"network", "live_smoke"})

    return inferred


def missing_profile_options(markers: set[str], enabled_profiles: dict[str, bool]) -> list[str]:
    return [
        OPTIONAL_PROFILE_OPTIONS[marker]
        for marker in _PROFILE_PRIORITY
        if marker in markers and not enabled_profiles.get(marker, False)
    ]


def profile_skip_reason(markers: set[str], enabled_profiles: dict[str, bool]) -> str | None:
    missing = missing_profile_options(markers, enabled_profiles)
    if not missing:
        return None
    joined = ", ".join(missing)
    return f"disabled by default; enable with {joined}"


def _is_live_smoke_test(test_name: str, file_name: str) -> bool:
    return (
        (file_name in _LIVE_SMOKE_TEST_FILES and test_name.startswith("test_live_"))
        or (file_name in _LIVE_SMOKE_TEST_FILES and "_live_" in test_name)
        or (file_name in _LIVE_SMOKE_TEST_FILES and test_name.endswith("_live"))
        or file_name == "test_tender_operator_agent_demo_acceptance_smoke.py"
    )
