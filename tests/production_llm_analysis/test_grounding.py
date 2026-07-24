from src.modules.production_llm_analysis.grounding import validate_provider_claims
from src.modules.production_llm_analysis.schemas import ProviderClaim, SupportStatus
from tests.production_llm_analysis.conftest import make_packet, make_reference


def test_exact_owned_evidence_supports_claim_with_validator_confidence():
    packet = make_packet()
    claim = ProviderClaim(
        claim_id="claim-1",
        field_path="line_items[0].name",
        value="Cable AVVG-P",
        provider_confidence=0.42,
        evidence_references=[make_reference(packet)],
    )

    result = validate_provider_claims(packet, [claim])[0]

    assert result.support_status == SupportStatus.SUPPORTED
    assert result.provider_confidence == 0.42
    assert result.validated_confidence == 0.95
    assert result.validation_errors == []


def test_cross_procurement_reference_is_rejected():
    packet = make_packet()
    claim = ProviderClaim(
        claim_id="claim-1",
        field_path="line_items[0].name",
        value="Cable AVVG-P",
        evidence_references=[make_reference(packet, procurement_case_id="other-case")],
    )

    result = validate_provider_claims(packet, [claim])[0]

    assert result.support_status == SupportStatus.REJECTED
    assert "reference_procurement_case_mismatch" in result.validation_errors
    assert result.validated_confidence is None


def test_quote_absent_from_fragment_is_rejected():
    packet = make_packet()
    claim = ProviderClaim(
        claim_id="claim-1",
        field_path="line_items[0].name",
        value="Invented item",
        evidence_references=[make_reference(packet, quote="Invented item")],
    )

    result = validate_provider_claims(packet, [claim])[0]

    assert result.support_status == SupportStatus.REJECTED
    assert "reference_quote_not_found" in result.validation_errors


def test_claim_value_must_be_lexically_supported_by_exact_quote():
    packet = make_packet()
    claim = ProviderClaim(
        claim_id="claim-1",
        field_path="line_items[0].quantity",
        value="999 meters",
        evidence_references=[make_reference(packet, quote="Cable AVVG-P quantity 10 meters")],
    )

    result = validate_provider_claims(packet, [claim])[0]

    assert result.support_status == SupportStatus.REJECTED
    assert "claim_value_not_lexically_supported" in result.validation_errors


def test_provider_only_assertion_is_insufficient_evidence():
    packet = make_packet()
    claim = ProviderClaim(
        claim_id="claim-1",
        field_path="contract.payment_term",
        value="30 calendar days",
        provider_confidence=1.0,
        evidence_references=[],
    )

    result = validate_provider_claims(packet, [claim])[0]

    assert result.support_status == SupportStatus.INSUFFICIENT_EVIDENCE
    assert result.validated_confidence is None
    assert "claim_has_no_evidence" in result.validation_errors


def test_positive_provider_decision_is_rejected_even_with_evidence():
    packet = make_packet()
    claim = ProviderClaim(
        claim_id="decision-1",
        field_path="bid_decision.recommendation",
        value="GO",
        provider_confidence=0.99,
        evidence_references=[make_reference(packet)],
    )

    result = validate_provider_claims(packet, [claim])[0]

    assert result.support_status == SupportStatus.REJECTED
    assert "provider_positive_decision_prohibited" in result.validation_errors
    assert result.validated_confidence is None


def test_duplicate_claim_ids_fail_closed():
    packet = make_packet()
    first = ProviderClaim(
        claim_id="same-id",
        field_path="line_items[0].name",
        value="Cable AVVG-P",
        evidence_references=[make_reference(packet)],
    )
    second = ProviderClaim(
        claim_id="same-id",
        field_path="line_items[0].quantity",
        value="10 meters",
        evidence_references=[make_reference(packet, quote="quantity 10 meters")],
    )

    results = validate_provider_claims(packet, [first, second])

    assert results[0].support_status == SupportStatus.SUPPORTED
    assert results[1].support_status == SupportStatus.REJECTED
    assert "duplicate_claim_id" in results[1].validation_errors
