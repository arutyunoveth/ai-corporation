from __future__ import annotations

import math

from src.modules.production_llm_analysis.evidence import canonical_json_bytes
from src.modules.production_llm_analysis.schemas import (
    BudgetEvaluation,
    BudgetPolicy,
    BudgetStatus,
    ProductionLLMAnalysisRequest,
    ProviderAnalysisResponse,
)


def _estimate_tokens(char_count: int, chars_per_token: int) -> int:
    return max(1, math.ceil(char_count / chars_per_token))


def _cost(policy: BudgetPolicy, input_tokens: int, output_tokens: int) -> float:
    pricing = policy.pricing
    value = (
        (input_tokens / 1000) * pricing.input_cost_per_1k_tokens
        + (output_tokens / 1000) * pricing.output_cost_per_1k_tokens
    )
    return round(value, 8)


def evaluate_preflight_budget(request: ProductionLLMAnalysisRequest) -> BudgetEvaluation:
    policy = request.budget_policy
    limits = policy.limits
    input_tokens = _estimate_tokens(
        len(canonical_json_bytes(request)),
        limits.chars_per_token_estimate,
    )
    output_tokens = limits.max_output_tokens
    estimated_cost = _cost(policy, input_tokens, output_tokens)
    reasons: list[str] = []

    if input_tokens > limits.max_input_tokens:
        reasons.append("estimated_input_tokens_exceed_limit")
    if estimated_cost > limits.max_estimated_cost:
        reasons.append("estimated_cost_exceeds_limit")

    return BudgetEvaluation(
        status=BudgetStatus.EXCEEDED if reasons else BudgetStatus.WITHIN_BUDGET,
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
        estimated_cost=estimated_cost,
        actual_or_reconciled_cost=estimated_cost,
        currency=policy.pricing.currency,
        pricing_table_version=policy.pricing.pricing_table_version,
        reasons=reasons,
    )


def reconcile_runtime_budget(
    request: ProductionLLMAnalysisRequest,
    response: ProviderAnalysisResponse,
    preflight: BudgetEvaluation,
) -> BudgetEvaluation:
    policy = request.budget_policy
    limits = policy.limits
    input_tokens = response.input_tokens
    output_tokens = response.output_tokens
    reconciled_input = input_tokens if input_tokens is not None else preflight.estimated_input_tokens
    reconciled_output = output_tokens if output_tokens is not None else preflight.estimated_output_tokens
    reconciled_cost = _cost(policy, reconciled_input, reconciled_output)
    reasons: list[str] = []

    if input_tokens is None or output_tokens is None:
        reasons.append("provider_usage_missing_estimate_used")
    if reconciled_input > limits.max_input_tokens:
        reasons.append("runtime_input_tokens_exceed_limit")
    if reconciled_output > limits.max_output_tokens:
        reasons.append("runtime_output_tokens_exceed_limit")
    if response.total_latency_ms > limits.max_total_latency_ms:
        reasons.append("runtime_latency_exceeds_limit")
    if reconciled_cost > limits.max_estimated_cost:
        reasons.append("runtime_cost_exceeds_limit")
    if response.retry_count > limits.max_retries:
        reasons.append("runtime_retry_count_exceeds_limit")

    exceeded = any(reason.endswith("exceed_limit") for reason in reasons)
    return BudgetEvaluation(
        status=BudgetStatus.EXCEEDED if exceeded else BudgetStatus.WITHIN_BUDGET,
        estimated_input_tokens=preflight.estimated_input_tokens,
        estimated_output_tokens=preflight.estimated_output_tokens,
        actual_input_tokens=input_tokens,
        actual_output_tokens=output_tokens,
        estimated_cost=preflight.estimated_cost,
        actual_or_reconciled_cost=reconciled_cost,
        currency=policy.pricing.currency,
        pricing_table_version=policy.pricing.pricing_table_version,
        total_latency_ms=response.total_latency_ms,
        reasons=reasons,
    )
