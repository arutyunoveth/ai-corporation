from __future__ import annotations

import re
from typing import Any, Iterable

from src.modules.production_llm_analysis.evidence import text_sha256
from src.modules.production_llm_analysis.schemas import (
    ConfidenceBasis,
    EvidencePacket,
    EvidenceReference,
    GroundedClaim,
    ProviderClaim,
    SupportStatus,
)

_POSITIVE_DECISIONS = {
    "GO",
    "GO_WITH_CONDITIONS",
    "READY",
    "APPROVED",
    "APPROVED_WITH_NOTES",
    "YES",
    "TRUE",
}
_DECISION_PATH_PARTS = {"bid_decision", "final_recommendation", "recommendation", "decision"}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _scalar_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, bool):
        return ["true" if value else "false"]
    if isinstance(value, (str, int, float)):
        return [str(value)]
    if isinstance(value, dict):
        scalars: list[str] = []
        for item in value.values():
            scalars.extend(_scalar_values(item))
        return scalars
    if isinstance(value, list):
        scalars = []
        for item in value:
            scalars.extend(_scalar_values(item))
        return scalars
    return [str(value)]


def _value_is_lexically_supported(value: Any, references: Iterable[EvidenceReference]) -> bool:
    quote_text = _normalize_text("\n".join(reference.quote for reference in references))
    scalar_values = [_normalize_text(item) for item in _scalar_values(value) if _normalize_text(item)]
    return bool(scalar_values) and all(item in quote_text for item in scalar_values)


def _is_prohibited_positive_decision(claim: ProviderClaim) -> bool:
    path_parts = {part.casefold() for part in re.split(r"[.\[\]/]", claim.field_path) if part}
    if not path_parts.intersection(_DECISION_PATH_PARTS):
        return False
    normalized_value = str(claim.value).strip().upper()
    return normalized_value in _POSITIVE_DECISIONS


def _validate_reference(packet: EvidencePacket, reference: EvidenceReference) -> list[str]:
    errors: list[str] = []
    fragments = {fragment.fragment_id: fragment for fragment in packet.fragments}
    fragment = fragments.get(reference.fragment_id)

    if reference.procurement_case_id != packet.procurement_case_id:
        errors.append("reference_procurement_case_mismatch")
    if reference.registry_number != packet.registry_number:
        errors.append("reference_registry_number_mismatch")
    if fragment is None:
        errors.append("reference_fragment_not_found")
        return errors
    if reference.document_id != fragment.document_id:
        errors.append("reference_document_id_mismatch")
    if reference.document_name != fragment.document_name:
        errors.append("reference_document_name_mismatch")
    if reference.chunk_id != fragment.chunk_id:
        errors.append("reference_chunk_id_mismatch")
    if reference.locator != fragment.locator:
        errors.append("reference_locator_mismatch")
    if text_sha256(reference.quote) != reference.quote_sha256:
        errors.append("reference_quote_hash_mismatch")
    if reference.quote not in fragment.text:
        errors.append("reference_quote_not_found")
    return errors


def validate_provider_claims(
    packet: EvidencePacket,
    claims: Iterable[ProviderClaim],
) -> list[GroundedClaim]:
    grounded: list[GroundedClaim] = []
    seen_claim_ids: set[str] = set()

    for claim in claims:
        errors: list[str] = []
        limitations: list[str] = []

        if claim.claim_id in seen_claim_ids:
            errors.append("duplicate_claim_id")
        seen_claim_ids.add(claim.claim_id)

        if _is_prohibited_positive_decision(claim):
            errors.append("provider_positive_decision_prohibited")
            grounded.append(
                GroundedClaim(
                    claim_id=claim.claim_id,
                    field_path=claim.field_path,
                    value=claim.value,
                    support_status=SupportStatus.REJECTED,
                    evidence_references=claim.evidence_references,
                    provider_confidence=claim.provider_confidence,
                    validated_confidence=None,
                    confidence_basis=ConfidenceBasis.PROHIBITED_DECISION,
                    validation_errors=errors,
                    limitations=["Positive participation decisions require a later deterministic decision policy."],
                )
            )
            continue

        if not claim.evidence_references:
            grounded.append(
                GroundedClaim(
                    claim_id=claim.claim_id,
                    field_path=claim.field_path,
                    value=claim.value,
                    support_status=SupportStatus.INSUFFICIENT_EVIDENCE,
                    provider_confidence=claim.provider_confidence,
                    validated_confidence=None,
                    confidence_basis=ConfidenceBasis.PROVIDER_ONLY_ASSERTION,
                    validation_errors=[*errors, "claim_has_no_evidence"],
                    limitations=["Provider-only assertions cannot enter canonical factual output."],
                )
            )
            continue

        for reference in claim.evidence_references:
            errors.extend(_validate_reference(packet, reference))

        if not errors and not _value_is_lexically_supported(claim.value, claim.evidence_references):
            errors.append("claim_value_not_lexically_supported")

        if errors:
            grounded.append(
                GroundedClaim(
                    claim_id=claim.claim_id,
                    field_path=claim.field_path,
                    value=claim.value,
                    support_status=SupportStatus.REJECTED,
                    evidence_references=claim.evidence_references,
                    provider_confidence=claim.provider_confidence,
                    validated_confidence=None,
                    confidence_basis=ConfidenceBasis.INCOMPLETE_EVIDENCE,
                    validation_errors=sorted(set(errors)),
                    limitations=limitations,
                )
            )
            continue

        multiple = len(claim.evidence_references) > 1
        grounded.append(
            GroundedClaim(
                claim_id=claim.claim_id,
                field_path=claim.field_path,
                value=claim.value,
                support_status=SupportStatus.SUPPORTED,
                evidence_references=claim.evidence_references,
                provider_confidence=claim.provider_confidence,
                validated_confidence=0.98 if multiple else 0.95,
                confidence_basis=(
                    ConfidenceBasis.MULTIPLE_EXACT_EVIDENCE
                    if multiple
                    else ConfidenceBasis.DIRECT_EXACT_EVIDENCE
                ),
                validation_errors=[],
                limitations=limitations,
            )
        )

    return grounded
