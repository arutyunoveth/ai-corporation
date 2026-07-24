from src.modules.production_llm_analysis.budgets import (
    evaluate_preflight_budget,
    reconcile_runtime_budget,
)
from src.modules.production_llm_analysis.schemas import BudgetStatus, ProviderAnalysisResponse
from tests.production_llm_analysis.conftest import make_policy, make_request


def test_preflight_budget_rejects_oversized_input():
    request = make_request(policy=make_policy(max_input_tokens=1))

    result = evaluate_preflight_budget(request)

    assert result.status == BudgetStatus.EXCEEDED
    assert "estimated_input_tokens_exceed_limit" in result.reasons
    assert result.estimated_input_tokens > 1


def test_runtime_latency_exceedance_is_fail_closed():
    request = make_request(policy=make_policy(max_total_latency_ms=100))
    preflight = evaluate_preflight_budget(request)
    response = ProviderAnalysisResponse(
        claims=[],
        input_tokens=100,
        output_tokens=50,
        total_latency_ms=101,
        retry_count=0,
    )

    result = reconcile_runtime_budget(request, response, preflight)

    assert result.status == BudgetStatus.EXCEEDED
    assert "runtime_latency_exceeds_limit" in result.reasons


def test_runtime_retry_exceedance_is_fail_closed():
    request = make_request(policy=make_policy(max_retries=0))
    preflight = evaluate_preflight_budget(request)
    response = ProviderAnalysisResponse(
        claims=[],
        input_tokens=100,
        output_tokens=50,
        total_latency_ms=10,
        retry_count=1,
    )

    result = reconcile_runtime_budget(request, response, preflight)

    assert result.status == BudgetStatus.EXCEEDED
    assert "runtime_retry_count_exceeds_limit" in result.reasons


def test_missing_provider_usage_is_estimated_not_reported_as_zero():
    request = make_request()
    preflight = evaluate_preflight_budget(request)
    response = ProviderAnalysisResponse(
        claims=[],
        input_tokens=None,
        output_tokens=None,
        total_latency_ms=10,
        retry_count=0,
    )

    result = reconcile_runtime_budget(request, response, preflight)

    assert result.status == BudgetStatus.WITHIN_BUDGET
    assert result.actual_input_tokens is None
    assert result.actual_output_tokens is None
    assert result.actual_or_reconciled_cost == preflight.estimated_cost
    assert result.actual_or_reconciled_cost > 0
    assert "provider_usage_missing_estimate_used" in result.reasons


def test_runtime_cost_exceedance_is_detected():
    request = make_request(policy=make_policy(max_estimated_cost=0.05))
    preflight = evaluate_preflight_budget(request)
    assert preflight.status == BudgetStatus.WITHIN_BUDGET
    response = ProviderAnalysisResponse(
        claims=[],
        input_tokens=100_000,
        output_tokens=1_000,
        total_latency_ms=10,
        retry_count=0,
    )

    result = reconcile_runtime_budget(request, response, preflight)

    assert result.status == BudgetStatus.EXCEEDED
    assert "runtime_cost_exceeds_limit" in result.reasons
