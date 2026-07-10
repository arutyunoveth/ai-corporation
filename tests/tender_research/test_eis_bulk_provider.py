from __future__ import annotations

import io
import zipfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.shared.db.base import Base
from src.tender_research.repository import TenderRepository
from src.tender_research.sync.providers.eis_getdocs_bulk import process_zip_payload


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
