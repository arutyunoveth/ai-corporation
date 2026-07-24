from __future__ import annotations

import socket
import urllib.request

from src.modules.production_llm_analysis.evidence import build_evidence_packet
from src.modules.production_llm_analysis.schemas import (
    AnalysisStatus,
    EvidenceFragmentInput,
    ProviderAnalysisResponse,
    ProviderClaim,
)
from src.modules.production_llm_analysis.service import run_production_llm_analysis
from tests.production_llm_analysis.conftest import (
    make_packet,
    make_policy,
    make_reference,
    make_request,
)


class _SuccessfulProvider:
    def __init__(self, *, total_latency_ms: int = 100):
        self.total_latency_ms = total_latency_ms
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        return ProviderAnalysisResponse(
            provider_request_id="provider-request-1",
            claims=[
                ProviderClaim(
                    claim_id="claim-1",
                    field_path="line_items[0].name",
                    value="Cable AVVG-P",
                    provider_confidence=0.99,
                    evidence_references=[make_reference(request.evidence_packet)],
                )
            ],
            input_tokens=100,
            output_tokens=20,
            attempt_latencies_ms=[self.total_latency_ms],
            total_latency_ms=self.total_latency_ms,
            retry_count=0,
            raw_response_sha256="a" * 64,
        )


class _InvalidProvider:
    def generate(self, request):
        _ = request
        return "not-a-valid-response"


class _TimeoutProvider:
    def generate(self, request):
        _ = request
        raise TimeoutError("sensitive provider detail")


class _UnavailableProvider:
    def generate(self, request):
        _ = request
        raise ConnectionError("host and credential detail")


def test_successful_grounded_result_is_deterministic_and_eligible():
    request = make_request()

    first = run_production_llm_analysis(request, _SuccessfulProvider())
    second = run_production_llm_analysis(request, _SuccessfulProvider())

    assert first.status == AnalysisStatus.SUCCESS
    assert first.canonical_input_eligible is True
    assert first.analysis_state == "needs_review"
    assert len(first.accepted_claims) == 1
    assert first.rejected_claims == []
    assert first.request_id == second.request_id
    assert first.evidence_packet_hash == second.evidence_packet_hash
    assert first.validated_result_hash == second.validated_result_hash


def test_preflight_budget_exceedance_prevents_provider_invocation():
    request = make_request(policy=make_policy(max_input_tokens=1))
    provider = _SuccessfulProvider()

    result = run_production_llm_analysis(request, provider)

    assert result.status == AnalysisStatus.BUDGET_EXCEEDED
    assert result.canonical_input_eligible is False
    assert result.sanitized_error_code == "budget_preflight_exceeded"
    assert provider.calls == 0


def test_timeout_is_sanitized_and_has_no_positive_fallback():
    result = run_production_llm_analysis(make_request(), _TimeoutProvider())

    assert result.status == AnalysisStatus.TIMEOUT
    assert result.analysis_state == "needs_review"
    assert result.canonical_input_eligible is False
    assert result.accepted_claims == []
    assert result.sanitized_error_code == "provider_timeout"
    assert "sensitive provider detail" not in str(result.model_dump(mode="json"))


def test_unavailable_provider_is_sanitized_and_has_no_stub_fallback():
    result = run_production_llm_analysis(make_request(), _UnavailableProvider())

    assert result.status == AnalysisStatus.PROVIDER_UNAVAILABLE
    assert result.canonical_input_eligible is False
    assert result.sanitized_error_code == "provider_unavailable"
    assert "credential detail" not in str(result.model_dump(mode="json"))


def test_invalid_provider_response_fails_closed():
    result = run_production_llm_analysis(make_request(), _InvalidProvider())

    assert result.status == AnalysisStatus.INVALID_RESPONSE
    assert result.canonical_input_eligible is False
    assert result.sanitized_error_code == "provider_response_invalid"


def test_runtime_budget_exceedance_blocks_canonical_input():
    request = make_request(policy=make_policy(max_total_latency_ms=10))

    result = run_production_llm_analysis(
        request,
        _SuccessfulProvider(total_latency_ms=11),
    )

    assert result.status == AnalysisStatus.BUDGET_EXCEEDED
    assert result.canonical_input_eligible is False
    assert result.sanitized_error_code == "runtime_budget_exceeded"


def test_positive_provider_decision_is_not_accepted():
    request = make_request()

    class _DecisionProvider:
        def generate(self, provider_request):
            return ProviderAnalysisResponse(
                claims=[
                    ProviderClaim(
                        claim_id="decision-1",
                        field_path="bid_decision.recommendation",
                        value="GO",
                        evidence_references=[make_reference(provider_request.evidence_packet)],
                    )
                ],
                input_tokens=100,
                output_tokens=10,
                total_latency_ms=10,
            )

    result = run_production_llm_analysis(request, _DecisionProvider())

    assert result.status == AnalysisStatus.VALIDATION_FAILED
    assert result.canonical_input_eligible is False
    assert result.accepted_claims == []
    assert result.rejected_claims[0].validation_errors == ["provider_positive_decision_prohibited"]


def test_gate_two_path_is_network_free_and_outbound_packet_is_redacted(monkeypatch):
    def _network_forbidden(*args, **kwargs):
        raise AssertionError(f"Network call attempted: {args!r} {kwargs!r}")

    monkeypatch.setattr(urllib.request, "urlopen", _network_forbidden)
    monkeypatch.setattr(socket, "create_connection", _network_forbidden)

    packet = build_evidence_packet(
        customer_id="customer-1",
        project_id="project-1",
        procurement_case_id="case-1",
        run_id="run-1",
        registry_number="0123456789012345678",
        fragments=[
            EvidenceFragmentInput(
                document_id="document-1",
                document_name="/Users/operator/private/specification.txt",
                chunk_id="chunk-1",
                locator={"page": 1},
                text="api_key=private-key Cable AVVG-P quantity 10 meters.",
            )
        ],
    )
    request = make_request(packet=packet)

    class _InspectingProvider(_SuccessfulProvider):
        def generate(self, provider_request):
            serialized = str(provider_request.model_dump(mode="json"))
            assert "private-key" not in serialized
            assert "/Users/operator" not in serialized
            return super().generate(provider_request)

    result = run_production_llm_analysis(request, _InspectingProvider())

    assert result.status == AnalysisStatus.SUCCESS
    serialized_result = result.model_dump(mode="json")
    assert "raw_response" not in serialized_result
    assert serialized_result["raw_response_sha256"] == "a" * 64
