from __future__ import annotations

from src.modules.production_llm_analysis.evidence import build_evidence_packet, text_sha256
from src.modules.production_llm_analysis.schemas import (
    BudgetLimits,
    BudgetPolicy,
    EvidenceFragmentInput,
    EvidenceReference,
    ProviderPricing,
)
from src.modules.production_llm_analysis.service import build_production_llm_request


def make_policy(**limit_overrides):
    values = {
        "max_input_tokens": 100_000,
        "max_output_tokens": 1_000,
        "timeout_ms": 5_000,
        "max_retries": 1,
        "max_total_latency_ms": 10_000,
        "max_estimated_cost": 10.0,
        "chars_per_token_estimate": 4,
    }
    values.update(limit_overrides)
    return BudgetPolicy(
        limits=BudgetLimits(**values),
        pricing=ProviderPricing(
            input_cost_per_1k_tokens=0.01,
            output_cost_per_1k_tokens=0.02,
            currency="USD",
            pricing_table_version="test-pricing-v1",
        ),
    )


def make_packet():
    return build_evidence_packet(
        customer_id="customer-1",
        project_id="project-1",
        procurement_case_id="case-1",
        run_id="run-1",
        registry_number="0123456789012345678",
        fragments=[
            EvidenceFragmentInput(
                document_id="document-1",
                document_name="specification.txt",
                chunk_id="chunk-1",
                locator={"page": 1, "paragraph": 2},
                text="Cable AVVG-P quantity 10 meters. Delivery term is 20 days.",
            ),
            EvidenceFragmentInput(
                document_id="document-2",
                document_name="contract.txt",
                chunk_id="chunk-2",
                locator={"page": 4, "paragraph": 8},
                text="Payment term is 30 calendar days after acceptance.",
            ),
        ],
    )


def make_request(*, packet=None, policy=None):
    packet = packet or make_packet()
    policy = policy or make_policy()
    return build_production_llm_request(
        evidence_packet=packet,
        provider="fake-provider",
        model="fake-model-v1",
        prompt_id="procurement-analysis",
        prompt_version="v1",
        output_schema_id="production-llm-analysis",
        output_schema_version="v1",
        grounding_policy_version="grounding-v1",
        budget_policy=policy,
    )


def make_reference(packet, *, quote="Cable AVVG-P", fragment_index=0, **overrides):
    fragment = packet.fragments[fragment_index]
    values = {
        "procurement_case_id": packet.procurement_case_id,
        "registry_number": packet.registry_number,
        "fragment_id": fragment.fragment_id,
        "document_id": fragment.document_id,
        "document_name": fragment.document_name,
        "chunk_id": fragment.chunk_id,
        "locator": fragment.locator,
        "quote": quote,
        "quote_sha256": text_sha256(quote),
    }
    values.update(overrides)
    return EvidenceReference(**values)
