import os
from pathlib import Path

import pytest

from src.modules.tender_operator_agent_demo.procurement_schemas import ProcurementSearchRequest
from src.modules.tender_operator_agent_demo.settings import ZakupkiSoapSettings
from src.modules.tender_operator_agent_demo.zakupki_soap_client import (
    ZakupkiSoapClient,
    parse_attachments_response,
    parse_details_response,
    parse_search_response,
)
from src.modules.tender_operator_agent_demo.zakupki_soap_templates import build_search_envelope


FIXTURES = Path(__file__).parent / "fixtures" / "zakupki_soap"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _settings(token: str = "test-token-value-not-real") -> ZakupkiSoapSettings:
    return ZakupkiSoapSettings(enabled=True, token=token, timeout_seconds=7, max_results=5)


def test_client_disabled_without_token():
    client = ZakupkiSoapClient(ZakupkiSoapSettings(enabled=True, token="replace_me_do_not_commit_real_token"))

    assert client.is_configured() is False
    assert client.search_procurements(ProcurementSearchRequest(query="кабель")) == []


def test_token_not_in_repr_status_or_errors():
    settings = _settings(token="secret-token-value")

    def failing_transport(_envelope: str, _soap_action: str | None, _timeout: int) -> str:
        raise RuntimeError("upstream rejected secret-token-value")

    client = ZakupkiSoapClient(settings, transport=failing_transport)

    assert "secret-token-value" not in repr(settings)
    assert "secret-token-value" not in str(settings.safe_status())
    with pytest.raises(RuntimeError) as excinfo:
        client.search_procurements(ProcurementSearchRequest(query="кабель"))
    assert "secret-token-value" not in str(excinfo.value)
    assert "[redacted]" in str(excinfo.value)


def test_search_envelope_contains_query_and_token_in_single_template_layer():
    envelope = build_search_envelope(
        ProcurementSearchRequest(query="шкаф управления", law="44-ФЗ", max_results=1),
        token="test-token-value-not-real",
    )

    assert "шкаф управления" in envelope
    assert "44-ФЗ" in envelope
    assert "test-token-value-not-real" in envelope
    assert "searchProcurements" in envelope


def test_mocked_search_xml_maps_to_normalized_results():
    results = parse_search_response(_fixture("search_response.xml"))

    assert len(results) == 1
    assert results[0].procurement_id == "eis-001"
    assert results[0].notice_number == "0373100000126000001"
    assert results[0].source == "zakupki_gov_ru_soap"
    assert results[0].can_download_attachments is True


def test_mocked_details_xml_maps_to_details():
    details = parse_details_response(_fixture("details_response.xml"))

    assert details.procurement.procurement_id == "eis-001"
    assert details.procurement.customer_name == "Промышленный заказчик"
    assert details.raw_source_summary == "Синтетическая карточка закупки для тестов SOAP parser."


def test_mocked_attachments_xml_maps_to_attachments():
    attachments = parse_attachments_response(_fixture("attachments_response.xml"))

    assert len(attachments) == 2
    assert attachments[0].attachment_id == "att-001"
    assert attachments[0].extension == ".txt"
    assert attachments[0].can_download is True


def test_soap_transport_uses_timeout_and_mocked_response():
    calls = []

    def transport(envelope: str, soap_action: str | None, timeout: int) -> str:
        calls.append((envelope, soap_action, timeout))
        return _fixture("search_response.xml")

    client = ZakupkiSoapClient(_settings(), transport=transport)
    results = client.search_procurements(ProcurementSearchRequest(query="кабель"))

    assert results
    assert calls[0][1] == "searchProcurements"
    assert calls[0][2] == 7


def test_xml_with_dtd_is_rejected():
    payload = """<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>"""

    with pytest.raises(ValueError, match="forbidden DTD"):
        parse_search_response(payload)


@pytest.mark.skipif(not os.getenv("ZAKUPKI_GOV_RU_SOAP_LIVE_TEST"), reason="live SOAP smoke is opt-in")
def test_live_zakupki_soap_search_smoke():
    settings = ZakupkiSoapSettings.from_env()
    client = ZakupkiSoapClient(settings)

    results = client.search_procurements(
        ProcurementSearchRequest(source="zakupki_gov_ru_soap", query="электротехническое оборудование", max_results=1)
    )

    assert isinstance(results, list)
