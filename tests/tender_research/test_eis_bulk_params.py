from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from src.modules.tender_operator_agent_demo.settings import ZakupkiSoapSettings
from src.modules.tender_operator_agent_demo.zakupki_soap_client import ZakupkiSoapClient
from src.tender_research.sync.eis_params import (
    EisParameterError,
    format_eis_create_datetime,
    format_eis_exact_date,
    normalize_eis_region_code,
)


def test_region_code_canonicalization():
    assert normalize_eis_region_code(77) == "77"
    assert normalize_eis_region_code("77") == "77"
    assert normalize_eis_region_code("770000000000") == "77"
    assert normalize_eis_region_code("Москва") == "77"
    assert normalize_eis_region_code("Санкт-Петербург") == "78"
    assert normalize_eis_region_code("Московская область") == "50"


def test_region_code_validation_error():
    with pytest.raises(EisParameterError):
        normalize_eis_region_code("bad")


def test_exact_date_requires_timezone_and_formats_moscow():
    assert format_eis_exact_date(date(2026, 7, 9), timezone="Europe/Moscow") == "2026-07-09+03:00"
    with pytest.raises(EisParameterError):
        format_eis_exact_date("2026-07-09")


def test_create_datetime_utc_without_microseconds():
    assert format_eis_create_datetime(datetime(2026, 7, 10, 10, 11, 12, 999, tzinfo=UTC)) == "2026-07-10T10:11:12Z"


def test_getdocs_org_region_request_uses_prod_uuid_canonical_region_and_tz():
    captured = {}

    def transport(envelope: str, _soap_action: str | None, _timeout: int) -> str:
        captured.setdefault("envelopes", []).append(envelope)
        return """<Envelope><Body><getDocsByOrgRegionResponse><index><id>server</id><refId>client</refId></index><dataInfo><archiveUrl>https://int.zakupki.gov.ru/archive.zip</archiveUrl></dataInfo></getDocsByOrgRegionResponse></Body></Envelope>"""

    settings = ZakupkiSoapSettings(enabled=True, token="individual", token_owner="individual", mode="PROD")
    client = ZakupkiSoapClient(settings, transport=transport)
    client.get_docs_by_org_region("770000000000", "2026-07-09", "epNotificationEF2020")
    client.get_docs_by_org_region("77", "2026-07-09+03:00", "epNotificationEF2020")

    first, second = captured["envelopes"]
    assert "<mode>PROD</mode>" in first
    assert "<orgRegion>77</orgRegion>" in first
    assert "<exactDate>2026-07-09+03:00</exactDate>" in first
    assert "<id>" in first
    assert first != second
