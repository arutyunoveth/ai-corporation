from __future__ import annotations

import io
import zipfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.shared.db.base import Base
from src.tender_research.repository import TenderRepository
from xml.etree import ElementTree as ET

from src.tender_research.sync.providers.eis_getdocs_bulk import process_zip_payload, parse_ep_notification_xml, _extract_attachments_from_xml


def _zip_payload(entries: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        for name, payload in entries.items():
            zf.writestr(name, payload)
    return out.getvalue()


def _xml(purchase_number: str, title: str = "Поставка кабеля") -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <export><epNotificationEF2020 schemeVersion="16.2">
      <commonInfo>
        <purchaseNumber>{purchase_number}</purchaseNumber>
        <publishDTInEIS>2026-07-09T10:00:00+03:00</publishDTInEIS>
        <href>https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber={purchase_number}</href>
        <placingWay><name>Электронный аукцион</name></placingWay>
        <purchaseObjectInfo>{title}</purchaseObjectInfo>
      </commonInfo>
      <customer><fullName>Заказчик</fullName><INN>7700000000</INN></customer>
      <lot><maxPrice>1000.00</maxPrice><currency><code>RUB</code></currency></lot>
    </epNotificationEF2020></export>""".encode()


def test_safe_zip_xml_partial_failure():
    payload = _zip_payload({"ok.xml": _xml("0373100134526000300"), "bad.xml": b"<broken"})
    results = process_zip_payload(payload)
    assert [item.status for item in results].count("parsed") == 1
    assert [item.status for item in results].count("failed") == 1


def test_repeated_sync_idempotent_and_changed_xml_versions():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    repo = TenderRepository(session)
    parsed = process_zip_payload(_zip_payload({"ok.xml": _xml("0373100134526000300")}))[0].tender
    _record, state = repo.upsert_tender_with_version(parsed)
    assert state == "inserted"
    _record, state = repo.upsert_tender_with_version(parsed)
    assert state == "unchanged"
    changed = process_zip_payload(_zip_payload({"ok.xml": _xml("0373100134526000300", "Поставка кабеля силового")}))[0].tender
    _record, state = repo.upsert_tender_with_version(changed)
    assert state == "updated"
    matches = repo.search_tenders(query="кабеля", source="eis_getdocs_bulk")
    assert len(matches) == 1


def _xml_with_attachments() -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<export><epNotificationEF2020 schemeVersion="16.2">'
        "<commonInfo>"
        "<purchaseNumber>0373100134526000300</purchaseNumber>"
        "<publishDTInEIS>2026-07-09T10:00:00+03:00</publishDTInEIS>"
        '<href>https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber=0373100134526000300</href>'
        "<placingWay><name>\u042d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u044b\u0439 \u0430\u0443\u043a\u0446\u0438\u043e\u043d</name></placingWay>"
        "<purchaseObjectInfo>\u041f\u043e\u0441\u0442\u0430\u0432\u043a\u0430 \u043a\u0430\u0431\u0435\u043b\u044f</purchaseObjectInfo>"
        "</commonInfo>"
        "<customer><fullName>\u0417\u0430\u043a\u0430\u0437\u0447\u0438\u043a</fullName><INN>7700000000</INN></customer>"
        "<lot><maxPrice>1000.00</maxPrice><currency><code>RUB</code></currency></lot>"
        "<attachmentsInfo>"
        "<attachmentInfo>"
        "<fileName>\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u043e\u0431\u044a\u0435\u043a\u0442\u0430 \u0437\u0430\u043a\u0443\u043f\u043a\u0438.docx</fileName>"
        "<url>https://zakupki.gov.ru/44fz/filestore/public/1.0/download/priz/file.html?uid=uid-001</url>"
        "<contentType>application/vnd.openxmlformats-officedocument.wordprocessingml.document</contentType>"
        "<size>102400</size>"
        "</attachmentInfo>"
        "<attachmentInfo>"
        "<fileName>\u041f\u0440\u043e\u0435\u043a\u0442 \u043a\u043e\u043d\u0442\u0440\u0430\u043a\u0442\u0430.pdf</fileName>"
        "<url>https://zakupki.gov.ru/44fz/filestore/public/1.0/download/priz/file.html?uid=uid-002</url>"
        "<contentType>application/pdf</contentType>"
        "<size>204800</size>"
        "</attachmentInfo>"
        "</attachmentsInfo>"
        "</epNotificationEF2020></export>"
    ).encode("utf-8")


def test_parse_ep_notification_with_attachments():
    result = parse_ep_notification_xml(_xml_with_attachments(), file_name="test.xml")
    raw = result["raw_payload"]
    assert "attachments" in raw
    assert len(raw["attachments"]) == 2
    assert raw["attachments"][0]["file_name"] == "Описание объекта закупки.docx"
    assert raw["attachments"][0]["file_url"] == "https://zakupki.gov.ru/44fz/filestore/public/1.0/download/priz/file.html?uid=uid-001"
    assert raw["attachments"][0]["content_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert raw["attachments"][0]["size_bytes"] == 102400
    assert raw["attachments"][1]["file_name"] == "Проект контракта.pdf"
    assert raw["attachments"][1]["size_bytes"] == 204800


def test_parse_ep_notification_no_attachments():
    result = parse_ep_notification_xml(_xml("0373100134526000300"), file_name="no-att.xml")
    raw = result["raw_payload"]
    assert "attachments" in raw
    assert raw["attachments"] == []


def test_process_zip_with_attachments():
    payload = _zip_payload({"notice.xml": _xml_with_attachments()})
    results = process_zip_payload(payload)
    assert len(results) == 1
    assert results[0].status == "parsed"
    tender = results[0].tender
    assert tender is not None
    attachments = tender["raw_payload"]["attachments"]
    assert len(attachments) == 2


def test_extract_attachments_deduplicates_by_url():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <export><epNotificationEF2020 schemeVersion="16.2">
      <commonInfo><purchaseNumber>test-001</purchaseNumber></commonInfo>
      <attachmentsInfo>
        <attachmentInfo><fileName>doc1.pdf</fileName><url>https://zakupki.gov.ru/filestore/doc.pdf</url></attachmentInfo>
        <attachmentInfo><fileName>doc1-dup.pdf</fileName><url>https://zakupki.gov.ru/filestore/doc.pdf</url></attachmentInfo>
      </attachmentsInfo>
    </epNotificationEF2020></export>"""
    root = ET.fromstring(xml)
    result = _extract_attachments_from_xml(root)
    assert len(result) == 1


def test_extract_attachments_no_content_type_size():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <export><epNotificationEF2020 schemeVersion="16.2">
      <commonInfo><purchaseNumber>test-002</purchaseNumber></commonInfo>
      <attachmentsInfo>
        <attachmentInfo><fileName>simple.txt</fileName><url>https://zakupki.gov.ru/filestore/simple.txt</url></attachmentInfo>
      </attachmentsInfo>
    </epNotificationEF2020></export>"""
    root = ET.fromstring(xml)
    result = _extract_attachments_from_xml(root)
    assert len(result) == 1
    assert result[0]["file_name"] == "simple.txt"
    assert result[0]["content_type"] is None
    assert result[0]["size_bytes"] is None


def test_extract_attachments_rejects_forbidden_schemes():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <export><epNotificationEF2020 schemeVersion="16.2">
      <commonInfo><purchaseNumber>test-003</purchaseNumber></commonInfo>
      <attachmentsInfo>
        <attachmentInfo><fileName>evil.js</fileName><url>javascript:alert(1)</url></attachmentInfo>
        <attachmentInfo><fileName>file.txt</fileName><url>file:///etc/passwd</url></attachmentInfo>
        <attachmentInfo><fileName>data.txt</fileName><url>data:text/plain;base64,SGVsbG8=</url></attachmentInfo>
      </attachmentsInfo>
    </epNotificationEF2020></export>"""
    root = ET.fromstring(xml)
    result = _extract_attachments_from_xml(root)
    assert len(result) == 0


def test_extract_attachments_rejects_unknown_host():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <export><epNotificationEF2020 schemeVersion="16.2">
      <commonInfo><purchaseNumber>test-004</purchaseNumber></commonInfo>
      <attachmentsInfo>
        <attachmentInfo><fileName>malware.exe</fileName><url>https://evil.ru/payload.exe</url></attachmentInfo>
      </attachmentsInfo>
    </epNotificationEF2020></export>"""
    root = ET.fromstring(xml)
    result = _extract_attachments_from_xml(root)
    assert len(result) == 0


def test_extract_attachments_allows_subdomains():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <export><epNotificationEF2020 schemeVersion="16.2">
      <commonInfo><purchaseNumber>test-005</purchaseNumber></commonInfo>
      <attachmentsInfo>
        <attachmentInfo><fileName>doc.pdf</fileName><url>https://int.zakupki.gov.ru/filestore/doc.pdf</url></attachmentInfo>
        <attachmentInfo><fileName>doc2.pdf</fileName><url>https://www.zakupki.gov.ru/filestore/doc2.pdf</url></attachmentInfo>
        <attachmentInfo><fileName>doc3.pdf</fileName><url>https://int44.zakupki.gov.ru/filestore/doc3.pdf</url></attachmentInfo>
      </attachmentsInfo>
    </epNotificationEF2020></export>"""
    root = ET.fromstring(xml)
    result = _extract_attachments_from_xml(root)
    assert len(result) == 3


def test_extract_attachments_ignores_empty_url_with_name():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <export><epNotificationEF2020 schemeVersion="16.2">
      <commonInfo><purchaseNumber>test-006</purchaseNumber></commonInfo>
      <attachmentsInfo>
        <attachmentInfo><fileName>nam_only.txt</fileName></attachmentInfo>
      </attachmentsInfo>
    </epNotificationEF2020></export>"""
    root = ET.fromstring(xml)
    result = _extract_attachments_from_xml(root)
    assert len(result) == 1
    assert result[0]["file_name"] == "nam_only.txt"
    assert result[0]["file_url"] is None
