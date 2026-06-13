from __future__ import annotations

from decimal import Decimal

from src.modules.price_normalization.normalize import (
    normalize_title,
    normalize_price,
    normalize_quantity,
    normalize_region,
    normalize_delivery_price,
    normalize_url,
)


class TestNormalizeTitle:
    def test_lowercases(self):
        assert normalize_title("Картридж HP") == "картридж hp"

    def test_strips_extra_spaces(self):
        assert normalize_title("  Много    пробелов  ") == "много пробелов"

    def test_removes_special_chars(self):
        result = normalize_title("Товар №1 (новый)!")
        assert "№" not in result
        assert "(" not in result

    def test_empty(self):
        assert normalize_title("") == ""

    def test_none(self):
        assert normalize_title(None) == ""


class TestNormalizePrice:
    def test_regular(self):
        assert normalize_price("1500.50") == Decimal("1500.50")

    def test_with_spaces(self):
        assert normalize_price("1 500") == Decimal("1500")

    def test_with_nbsp(self):
        assert normalize_price("1\u00a0500") == Decimal("1500")

    def test_comma_separator(self):
        assert normalize_price("1500,50") == Decimal("1500.50")

    def test_none(self):
        assert normalize_price(None) is None

    def test_empty(self):
        assert normalize_price("") is None

    def test_int_input(self):
        assert normalize_price(1500) == Decimal("1500")


class TestNormalizeQuantity:
    def test_regular(self):
        qty, flags = normalize_quantity("10")
        assert qty == Decimal("10")
        assert flags == []

    def test_unknown(self):
        qty, flags = normalize_quantity(None)
        assert qty == Decimal("1")
        assert "quantity_unknown" in flags


class TestNormalizeRegion:
    def test_regular(self):
        region, flags = normalize_region("Москва")
        assert region == "Москва"
        assert flags == []

    def test_unknown(self):
        region, flags = normalize_region("")
        assert region is None
        assert "region_unknown" in flags

    def test_none(self):
        region, flags = normalize_region(None)
        assert region is None


class TestNormalizeDeliveryPrice:
    def test_regular(self):
        price, flags = normalize_delivery_price("500")
        assert price == Decimal("500")
        assert flags == []

    def test_unknown_uses_default(self):
        price, flags = normalize_delivery_price(None)
        assert price == Decimal("500")
        assert "delivery_unknown" in flags

    def test_custom_default(self):
        price, flags = normalize_delivery_price(None, default_unknown_cost="1000")
        assert price == Decimal("1000")


class TestNormalizeUrl:
    def test_adds_scheme(self):
        url = normalize_url("HTTP://Example.COM/Page")
        assert url == "http://example.com/Page"

    def test_lowercases_netloc(self):
        url = normalize_url("https://Example.COM/Page")
        assert "example.com" in url

    def test_removes_fragment(self):
        url = normalize_url("https://example.com/page#section")
        assert "#section" not in url

    def test_none(self):
        assert normalize_url(None) is None

    def test_empty(self):
        assert normalize_url("") is None
