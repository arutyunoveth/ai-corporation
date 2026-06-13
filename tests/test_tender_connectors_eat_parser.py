from __future__ import annotations

from decimal import Decimal

import pytest

from src.modules.tender_connectors.eat.parser import (
    parse_purchase_payload,
    parse_item_payload,
    _pick,
    _parse_decimal,
    _parse_datetime,
)


class TestEatParserPick:
    def test_pick_returns_first_match(self):
        raw = {"a": "1", "b": "2"}
        assert _pick(raw, ["a", "b"]) == "1"

    def test_pick_returns_none_when_no_match(self):
        assert _pick({"a": ""}, ["b", "c"]) is None

    def test_pick_skips_empty(self):
        assert _pick({"a": "", "b": "val"}, ["a", "b"]) == "val"


class TestEatParserDecimal:
    def test_parse_regular(self):
        assert _parse_decimal("1234.56") == Decimal("1234.56")

    def test_parse_with_spaces(self):
        assert _parse_decimal("1 234,56") == Decimal("1234.56")

    def test_parse_nbsp(self):
        assert _parse_decimal("1\u00a0234") == Decimal("1234")

    def test_parse_none(self):
        assert _parse_decimal(None) is None

    def test_parse_empty(self):
        assert _parse_decimal("") is None


class TestEatParserDatetime:
    def test_iso_format(self):
        dt = _parse_datetime("2026-06-13T15:30:00")
        assert dt is not None
        assert dt.hour == 15
        assert dt.minute == 30

    def test_iso_with_z(self):
        dt = _parse_datetime("2026-06-13T15:30:00Z")
        assert dt is not None
        assert dt.hour == 15

    def test_russian_format(self):
        dt = _parse_datetime("13.06.2026 15:30")
        assert dt is not None
        assert dt.day == 13
        assert dt.month == 6

    def test_date_only_format(self):
        dt = _parse_datetime("13.06.2026")
        assert dt is not None
        assert dt.day == 13

    def test_none(self):
        assert _parse_datetime(None) is None


class TestEatParserItem:
    def test_parse_basic_item(self):
        item = parse_item_payload({
            "name": "Картридж HP 305A",
            "quantity": "10",
            "unit": "шт",
            "maxUnitPrice": "3500.00",
            "maxTotalPrice": "35000.00",
        })
        assert item.name == "Картридж HP 305A"
        assert item.quantity == Decimal("10")
        assert item.unit == "шт"
        assert item.max_unit_price == Decimal("3500.00")
        assert item.max_total_price == Decimal("35000.00")

    def test_parse_item_requires_name(self):
        with pytest.raises(ValueError, match="item name required"):
            parse_item_payload({"quantity": "1"})

    def test_parse_item_default_quantity(self):
        item = parse_item_payload({"name": "Test"})
        assert item.quantity == Decimal("1")

    def test_parse_item_with_okpd2(self):
        item = parse_item_payload({"name": "Test", "okpd2": "26.20.1"})
        assert item.okpd2 == "26.20.1"

    def test_parse_item_with_delivery_info(self):
        item = parse_item_payload({
            "name": "Test",
            "quantity": "5",
            "deliveryRegion": "Москва",
            "deliveryAddress": "ул. Тестовая, д.1",
        })
        assert item.delivery_region == "Москва"
        assert item.delivery_address == "ул. Тестовая, д.1"


class TestEatParserPurchase:
    def test_parse_basic_purchase(self):
        purchase = parse_purchase_payload({
            "externalId": "EAT-12345",
            "title": "Поставка картриджей",
            "status": "Прием предложений",
            "maxTotalPrice": "500000.00",
            "items": [
                {"name": "Картридж HP 305A", "quantity": "10", "maxUnitPrice": "3500.00"},
                {"name": "Картридж Canon 045", "quantity": "5", "maxUnitPrice": "2800.00"},
            ],
        })
        assert purchase.source == "eat"
        assert purchase.external_id == "EAT-12345"
        assert purchase.title == "Поставка картриджей"
        assert purchase.max_total_price == Decimal("500000.00")
        assert len(purchase.items) == 2

    def test_parse_with_lot_items(self):
        purchase = parse_purchase_payload({
            "announcementId": "EAT-67890",
            "purchaseName": "Тестовая закупка",
            "lotItems": [{"name": "Тестовый товар", "quantity": "3", "price": "1000.00"}],
        })
        assert purchase.external_id == "EAT-67890"
        assert len(purchase.items) == 1

    def test_parse_with_organizer(self):
        purchase = parse_purchase_payload({
            "externalId": "EAT-111",
            "title": "Test",
            "organizerInfo": {"name": "ООО Организатор"},
        })
        assert purchase.customer_name == "ООО Организатор"

    def test_parse_minimal(self):
        purchase = parse_purchase_payload({"externalId": "EAT-1"})
        assert purchase.external_id == "EAT-1"
        assert purchase.title is not None
        assert purchase.items == []

    def test_parse_empty_skips_bad_items(self):
        purchase = parse_purchase_payload({
            "externalId": "EAT-1",
            "items": [None, {}, {"name": "Good Item", "quantity": "1"}],
        })
        assert len(purchase.items) == 1
        assert purchase.items[0].name == "Good Item"

    def test_parse_url_built(self):
        purchase = parse_purchase_payload({"externalId": "EAT-123"})
        assert purchase.url == "https://agregatoreat.ru/purchases/announcement/EAT-123"

    def test_parse_with_all_fields(self):
        purchase = parse_purchase_payload({
            "externalId": "EAT-FULL",
            "title": "Полная закупка",
            "url": "https://example.com/purchase/1",
            "status": "Прием предложений",
            "region": "Москва",
            "customerName": "ООО Заказчик",
            "submissionDeadline": "2026-07-01T12:00:00",
            "commissionFeeAmount": "1000.00",
            "securityAmount": "50000.00",
            "maxTotalPrice": "1000000.00",
            "createdAt": "2026-06-01T10:00:00",
        })
        assert purchase.url == "https://example.com/purchase/1"
        assert purchase.region == "Москва"
        assert purchase.commission_fee_amount == Decimal("1000.00")
        assert purchase.security_amount == Decimal("50000.00")
        assert purchase.submission_deadline is not None
        assert purchase.created_at_source is not None
