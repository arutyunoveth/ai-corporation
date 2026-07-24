from src.modules.production_llm_analysis.evidence import build_evidence_packet
from src.modules.production_llm_analysis.schemas import EvidenceFragmentInput


def test_evidence_packet_is_deterministic_across_input_order():
    fragments = [
        EvidenceFragmentInput(
            document_id="doc-b",
            document_name="b.txt",
            chunk_id="chunk-2",
            locator={"page": 2},
            text="Second evidence fragment.",
        ),
        EvidenceFragmentInput(
            document_id="doc-a",
            document_name="a.txt",
            chunk_id="chunk-1",
            locator={"page": 1},
            text="First evidence fragment.",
        ),
    ]
    kwargs = {
        "customer_id": "customer-1",
        "project_id": "project-1",
        "procurement_case_id": "case-1",
        "run_id": "run-1",
        "registry_number": "0123456789012345678",
    }

    first = build_evidence_packet(fragments=fragments, **kwargs)
    second = build_evidence_packet(fragments=reversed(fragments), **kwargs)

    assert first.packet_hash == second.packet_hash
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [fragment.document_id for fragment in first.fragments] == ["doc-a", "doc-b"]


def test_evidence_packet_removes_credentials_and_local_paths():
    packet = build_evidence_packet(
        customer_id="customer-1",
        project_id="project-1",
        procurement_case_id="case-1",
        run_id="run-1",
        registry_number="0123456789012345678",
        fragments=[
            EvidenceFragmentInput(
                document_id="doc-1",
                document_name="/Users/operator/private/specification.txt",
                chunk_id="chunk-1",
                locator={"page": 1},
                text=(
                    "Authorization: Bearer super-secret-token\n"
                    "api_key=private-value\n"
                    "source=/home/operator/customer/raw.txt\n"
                    "Cable AVVG-P quantity 10 meters."
                ),
            )
        ],
    )

    serialized = str(packet.model_dump(mode="json"))
    assert "super-secret-token" not in serialized
    assert "private-value" not in serialized
    assert "/Users/operator" not in serialized
    assert "/home/operator" not in serialized
    assert packet.fragments[0].document_name == "specification.txt"
    assert "[REDACTED_SECRET]" in packet.fragments[0].text
    assert "[REDACTED_PATH]" in packet.fragments[0].text
    assert packet.data_handling.redaction_applied is True
    assert packet.data_handling.redaction_count >= 4


def test_evidence_packet_rejects_duplicate_fragments():
    fragment = EvidenceFragmentInput(
        document_id="doc-1",
        document_name="specification.txt",
        chunk_id="chunk-1",
        locator={"page": 1},
        text="Same exact fragment.",
    )

    try:
        build_evidence_packet(
            customer_id="customer-1",
            project_id="project-1",
            procurement_case_id="case-1",
            run_id="run-1",
            registry_number="0123456789012345678",
            fragments=[fragment, fragment],
        )
    except ValueError as exc:
        assert str(exc) == "Evidence packet contains duplicate fragments"
    else:
        raise AssertionError("Duplicate evidence fragments must be rejected")
