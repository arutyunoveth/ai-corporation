from pytest_optional_profiles import infer_optional_test_markers, missing_profile_options, profile_skip_reason


def test_infer_optional_test_markers_for_generic_integration_file():
    markers = infer_optional_test_markers("tests/test_sprint1_integration.py::test_flow")

    assert markers == {"integration"}


def test_infer_optional_test_markers_for_postgres_file_is_specific():
    markers = infer_optional_test_markers("tests/tender_research/test_postgres_pgvector_integration.py::test_smoke")

    assert markers == {"postgres"}


def test_infer_optional_test_markers_for_llama_cpp_cases():
    markers = infer_optional_test_markers("tests/tender_research/test_rag_embedding_server_cli.py::test_check_embedding_server_llama_cpp_success")

    assert markers == {"llama_cpp"}


def test_infer_optional_test_markers_for_live_smoke_requires_network_too():
    markers = infer_optional_test_markers("tests/test_tender_operator_agent_zakupki_soap_client.py::test_live_zakupki_soap_search_smoke")

    assert markers == {"live_smoke", "network"}


def test_missing_profile_options_respects_priority():
    missing = missing_profile_options(
        {"live_smoke", "network"},
        {
            "integration": False,
            "postgres": False,
            "network": False,
            "llama_cpp": False,
            "live_smoke": False,
        },
    )

    assert missing == ["--run-live-smoke", "--run-network"]


def test_profile_skip_reason_is_empty_when_profiles_enabled():
    reason = profile_skip_reason(
        {"llama_cpp"},
        {
            "integration": False,
            "postgres": False,
            "network": False,
            "llama_cpp": True,
            "live_smoke": False,
        },
    )

    assert reason is None
