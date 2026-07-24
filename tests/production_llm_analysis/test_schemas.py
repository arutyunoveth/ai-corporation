import pytest
from pydantic import ValidationError

from src.modules.production_llm_analysis.schemas import ProviderClaim
from src.modules.production_llm_analysis.service import build_production_llm_request
from tests.production_llm_analysis.conftest import make_packet, make_policy, make_request


def test_contract_schemas_forbid_unknown_fields():
    with pytest.raises(ValidationError):
        ProviderClaim(
            claim_id="claim-1",
            field_path="summary.subject",
            value="Cable AVVG-P",
            unexpected="not-allowed",
        )


def test_production_request_forces_temperature_zero():
    request = make_request()
    payload = request.model_dump(mode="json")
    payload["temperature"] = 0.1

    with pytest.raises(ValidationError):
        type(request).model_validate(payload)


def test_request_identity_is_stable_for_identical_inputs():
    packet = make_packet()
    policy = make_policy()

    first = build_production_llm_request(
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
    second = build_production_llm_request(
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

    assert first.request_id == second.request_id


def test_request_identity_changes_when_versioned_input_changes():
    packet = make_packet()
    policy = make_policy()
    first = make_request(packet=packet, policy=policy)
    changed = build_production_llm_request(
        evidence_packet=packet,
        provider=first.provider,
        model="fake-model-v2",
        prompt_id=first.prompt_id,
        prompt_version=first.prompt_version,
        output_schema_id=first.output_schema_id,
        output_schema_version=first.output_schema_version,
        grounding_policy_version=first.grounding_policy_version,
        budget_policy=policy,
    )

    assert first.request_id != changed.request_id
