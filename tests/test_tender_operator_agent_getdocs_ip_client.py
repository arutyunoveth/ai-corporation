import os

import pytest

from src.modules.tender_operator_agent_demo.procurement_schemas import DocsArchiveResult
from src.modules.tender_operator_agent_demo.settings import ZakupkiSoapSettings
from src.modules.tender_operator_agent_demo.zakupki_soap_client import (
    ZakupkiSoapClient,
    parse_getdocs_response,
)


def _settings(token: str = "test-token-value-not-real") -> ZakupkiSoapSettings:
    return ZakupkiSoapSettings(
        enabled=True,
        token=token,
        token_owner="individual",
        individual_base_url="https://int44.zakupki.gov.ru/eis-integration/services/getDocsIP",
        individual_xsd_url="https://int44.zakupki.gov.ru/eis-integration/services/getDocsIP?xsd=getDocsIP-ws-api.xsd",
        individual_namespace="http://zakupki.gov.ru/fz44/get-docs-ip/ws",
        token_header_name="individualPerson_token",
        mode="PROD",
        timeout_seconds=7,
    )


def test_getdocs_response_parser_extracts_archive_url():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
      <soapenv:Body>
        <ns2:getDocsByReestrNumberResponse xmlns:ns2="http://zakupki.gov.ru/fz44/get-docs-ip/ws">
          <index>
            <id>req-001</id>
            <refId>ref-001</refId>
          </index>
          <dataInfo>
            <archiveUrl>https://int44.zakupki.gov.ru/archive/demo.zip</archiveUrl>
          </dataInfo>
        </ns2:getDocsByReestrNumberResponse>
      </soapenv:Body>
    </soapenv:Envelope>"""

    result = parse_getdocs_response(
        xml,
        request_id="req-001",
        expected_response_tag="getDocsByReestrNumberResponse",
        expected_request_tag="getDocsByReestrNumberRequest",
    )

    assert result.request_id == "req-001"
    assert result.ref_id == "ref-001"
    assert result.archive_url == "https://int44.zakupki.gov.ru/archive/demo.zip"
    assert result.status == "completed"


def test_getdocs_response_parser_handles_soap_fault():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
      <soapenv:Body>
        <soapenv:Fault>
          <faultcode>soap:Client</faultcode>
          <faultstring>Validation failed</faultstring>
        </soapenv:Fault>
      </soapenv:Body>
    </soapenv:Envelope>"""

    result = parse_getdocs_response(
        xml,
        request_id="req-002",
        expected_response_tag="getDocsByReestrNumberResponse",
        expected_request_tag="getDocsByReestrNumberRequest",
    )

    assert result.status == "soap_fault"
    assert result.archive_url is None


def test_getdocs_response_parser_handles_validation_error():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Envelope>
      <Body>
        <errorMessage>Schema validation error: invalid order of selectionParams</errorMessage>
      </Body>
    </Envelope>"""

    result = parse_getdocs_response(
        xml,
        request_id="req-003",
        expected_response_tag="getDocsByReestrNumberResponse",
        expected_request_tag="getDocsByReestrNumberRequest",
    )

    assert result.status == "validation_error"


def test_getdocs_response_parser_handles_missing_archive_url():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Envelope>
      <Body>
        <getDocsByReestrNumberResponse>
          <index><id>req-004</id></index>
          <dataInfo></dataInfo>
        </getDocsByReestrNumberResponse>
      </Body>
    </Envelope>"""

    result = parse_getdocs_response(
        xml,
        request_id="req-004",
        expected_response_tag="getDocsByReestrNumberResponse",
        expected_request_tag="getDocsByReestrNumberRequest",
    )

    assert result.status == "no_archive_url"
    assert result.archive_url is None


def test_download_archive_uses_individual_token_header(tmp_path):
    captured = {}

    def http_transport(url: str, headers: dict[str, str], timeout: int, max_bytes: int):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        captured["max_bytes"] = max_bytes
        return b"PK\x03\x04demo", "application/zip"

    client = ZakupkiSoapClient(_settings(), http_transport=http_transport)
    downloaded = client.download_archive("https://int44.zakupki.gov.ru/archive/demo.zip", tmp_path)

    assert captured["headers"]["individualPerson_token"] == "test-token-value-not-real"
    assert downloaded.stored_name == "documentation-archive.zip"
    assert downloaded.size_bytes > 0


def test_getdocs_client_transport_error_sanitizes_token():
    secret = "secret-token-value"

    def failing_transport(_envelope: str, _soap_action: str | None, _timeout: int) -> str:
        raise RuntimeError(f"upstream rejected {secret}")

    client = ZakupkiSoapClient(_settings(secret), transport=failing_transport)

    with pytest.raises(RuntimeError) as excinfo:
        client.get_docs_by_reestr_number("0888200000224000038")

    assert secret not in str(excinfo.value)
    assert "[redacted]" in str(excinfo.value)


@pytest.mark.skipif(not os.getenv("ZAKUPKI_GOV_RU_SOAP_LIVE_TEST"), reason="live getDocsIP smoke is opt-in")
def test_live_getdocsip_smoke():
    settings = ZakupkiSoapSettings.from_env()
    client = ZakupkiSoapClient(settings)

    try:
        result = client.get_docs_by_reestr_number("0888200000224000038")
    except RuntimeError as exc:
        message = str(exc)
        assert "SOAP-запрос к ЕИС завершился ошибкой:" in message
        assert "[redacted]" not in message
    else:
        assert isinstance(result, DocsArchiveResult)
