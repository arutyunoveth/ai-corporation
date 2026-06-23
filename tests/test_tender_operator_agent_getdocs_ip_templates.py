from src.modules.tender_operator_agent_demo.zakupki_soap_templates import (
    build_get_docs_by_org_region_envelope,
    build_get_docs_by_reestr_number_envelope,
)


def test_getdocs_by_reestr_number_envelope_contains_individual_token_and_namespace():
    envelope = build_get_docs_by_reestr_number_envelope(
        token="test-token-value-not-real",
        namespace="http://zakupki.gov.ru/fz44/get-docs-ip/ws",
        token_header_name="individualPerson_token",
        request_id="req-001",
        created_time="2026-06-23T10:00:00+00:00",
        mode="PROD",
        reestr_number="0888200000224000038",
        subsystem_type="PRIZ",
    )

    assert "<individualPerson_token>test-token-value-not-real</individualPerson_token>" in envelope
    assert 'xmlns:ws="http://zakupki.gov.ru/fz44/get-docs-ip/ws"' in envelope
    assert "<ws:getDocsByReestrNumberRequest>" in envelope
    assert envelope.index("<selectionParams>") < envelope.index("<subsystemType>PRIZ</subsystemType>") < envelope.index(
        "<reestrNumber>0888200000224000038</reestrNumber>"
    )


def test_getdocs_by_org_region_envelope_preserves_required_selection_order():
    envelope = build_get_docs_by_org_region_envelope(
        token="test-token-value-not-real",
        namespace="http://zakupki.gov.ru/fz44/get-docs-ip/ws",
        token_header_name="individualPerson_token",
        request_id="req-002",
        created_time="2026-06-23T10:00:00+00:00",
        mode="PROD",
        org_region="72",
        exact_date="2024-12-24",
        document_type44="epNotificationEF2020",
        subsystem_type="PRIZ",
    )

    assert "<ws:getDocsByOrgRegionRequest>" in envelope
    assert envelope.index("<orgRegion>72</orgRegion>") < envelope.index("<subsystemType>PRIZ</subsystemType>")
    assert envelope.index("<subsystemType>PRIZ</subsystemType>") < envelope.index(
        "<documentType44>epNotificationEF2020</documentType44>"
    )
    assert "<exactDate>2024-12-24</exactDate>" in envelope
