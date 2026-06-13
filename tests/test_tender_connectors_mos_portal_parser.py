from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.tender_connectors.mos_portal.parser import (
    parse_purchase_payload,
    parse_item_payload,
    _pick_external_id,
    _resolve_status,
)


class TestMosPortalParserItem:
    def test_parse_basic_item(self):
        item = parse_item_payload({
            "name": "Бумага А4",
            "quantity": "100",
            "unit": "пач",
            "maxUnitPrice": "350.00",
            "maxTotalPrice": "35000.00",
        })
        assert item.name == "Бумага А4"
        assert item.quantity == Decimal("100")
        assert item.max_unit_price == Decimal("350.00")

    def test_parse_item_requires_name(self):
        with pytest.raises(ValueError, match="item name required"):
            parse_item_payload({"quantity": "1"})

    def test_parse_item_default_quantity(self):
        item = parse_item_payload({"name": "Test"})
        assert item.quantity == Decimal("1")

    def test_parse_item_with_trade_name(self):
        item = parse_item_payload({"tradeName": "Специальный товар", "quantity": "2"})
        assert item.name == "Специальный товар"


class TestMosPortalParserPurchase:
    def test_parse_basic_purchase(self):
        purchase = parse_purchase_payload({
            "externalId": "MOS-12345",
            "title": "Поставка офисной бумаги",
            "status": "Прием предложений",
            "maxTotalPrice": "100000.00",
            "items": [
                {"name": "Бумага А4", "quantity": "100", "maxUnitPrice": "350.00"},
            ],
        })
        assert purchase.source == "mos_portal"
        assert purchase.external_id == "MOS-12345"
        assert purchase.title == "Поставка офисной бумаги"
        assert purchase.max_total_price == Decimal("100000.00")
        assert len(purchase.items) == 1

    def test_parse_with_state_id(self):
        purchase = parse_purchase_payload({
            "id": "MOS-99",
            "name": "Test",
            "stateId": 19000002,
        })
        assert purchase.status == "Прием предложений"

    def test_parse_external_id_variants(self):
        assert _pick_external_id({"auctionId": "AUC-001"}) == "AUC-001"
        assert _pick_external_id({"purchaseNumber": "PN-001"}) == "PN-001"
        assert _pick_external_id({"sessionId": "SES-001"}) == "SES-001"

    def test_status_active(self):
        assert _resolve_status({"status": "Активная"}) == "Прием предложений"

    def test_status_pass_through(self):
        assert _resolve_status({"status": "Завершен"}) == "Завершен"

    def test_status_from_state_dict(self):
        assert _resolve_status({"state": {"name": "Активная"}}) == "Прием предложений"

    def test_status_none_when_missing(self):
        assert _resolve_status({}) is None

    def test_parse_url_from_raw(self):
        purchase = parse_purchase_payload({
            "id": "MOS-1",
            "title": "Test",
            "url": "https://zakupki.mos.ru/auction/123",
        })
        assert purchase.url == "https://zakupki.mos.ru/auction/123"

    def test_parse_url_built(self):
        purchase = parse_purchase_payload({"id": "MOS-1", "title": "Test"})
        assert "zakupki.mos.ru" in (purchase.url or "")

    def test_parse_with_all_fields(self):
        purchase = parse_purchase_payload({
            "id": "MOS-FULL",
            "title": "Полная закупка МОС",
            "status": "Прием предложений",
            "region": "Москва",
            "customerName": "ГБУ ЖКХ",
            "submissionDeadline": "2026-07-01T12:00:00",
            "maxTotalPrice": "2000000.00",
            "commissionFeeAmount": "2000.00",
            "items": [{"name": "Услуги", "quantity": "1"}],
        })
        assert purchase.region == "Москва"
        assert purchase.customer_name == "ГБУ ЖКХ"
        assert purchase.commission_fee_amount == Decimal("2000.00")
        assert purchase.max_total_price == Decimal("2000000.00")
