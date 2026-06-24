import json
import os

import pytest

from src.modules.tender_operator_agent_demo.supplier_profile import (
    RiskTolerance,
    SupplierProfile,
    SupplierProfileCriteria,
    SupplierProfileRiskPreferences,
)

FIXTURE_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "demo_data",
        "tender_operator_agent",
        "supplier_profile_electrical.json",
    )
)


def test_supplier_profile_defaults():
    profile = SupplierProfile(supplier_id="test-001", name="Test Supplier")
    assert profile.supplier_id == "test-001"
    assert profile.name == "Test Supplier"
    assert profile.short_name is None
    assert profile.inn is None
    assert profile.criteria.categories == []
    assert profile.criteria.price_min is None
    assert profile.criteria.price_max is None
    assert profile.criteria.keywords == []
    assert profile.criteria.stop_words == []
    assert profile.risk_preferences.tolerance == RiskTolerance.MEDIUM
    assert profile.risk_preferences.max_penalty_percent is None
    assert profile.risk_preferences.require_certificates is True
    assert profile.certificates == []
    assert profile.metadata == {}


def test_supplier_profile_criteria_validation():
    criteria = SupplierProfileCriteria(
        categories=["Электротехника", "Кабели"],
        regions=["Москва"],
        price_min=100_000.0,
        price_max=15_000_000.0,
        keywords=["кабель", "шкаф"],
        stop_words=["строительный", "мебель"],
    )
    assert "Электротехника" in criteria.categories
    assert criteria.price_min == 100_000.0
    assert criteria.price_max == 15_000_000.0
    assert "строительный" in criteria.stop_words


def test_supplier_profile_risk_preferences_validation():
    risk = SupplierProfileRiskPreferences(
        tolerance=RiskTolerance.LOW,
        max_penalty_percent=5.0,
        max_delay_days=30,
        require_certificates=True,
    )
    assert risk.tolerance == RiskTolerance.LOW
    assert risk.max_penalty_percent == 5.0
    assert risk.max_delay_days == 30

    risk_high = SupplierProfileRiskPreferences(tolerance=RiskTolerance.HIGH)
    assert risk_high.tolerance == RiskTolerance.HIGH
    assert risk_high.max_penalty_percent is None


def test_demo_fixture_file_exists():
    assert os.path.isfile(FIXTURE_PATH), f"Fixture file not found at {FIXTURE_PATH}"


def test_demo_fixture_valid_json():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert "supplier_id" in data
    assert "name" in data
    assert "criteria" in data
    assert "risk_preferences" in data


def test_demo_fixture_loads_as_supplier_profile():
    profile = SupplierProfile.load_demo_fixture()
    assert profile.supplier_id == "demo-supplier-electrical-001"
    assert profile.name == "Демо-поставщик электротехнического оборудования"
    assert profile.inn == "7728123456"
    assert len(profile.criteria.categories) >= 3
    assert len(profile.criteria.regions) >= 1
    assert profile.criteria.price_min == 100_000
    assert profile.criteria.price_max == 15_000_000
    assert len(profile.criteria.keywords) >= 3
    assert len(profile.criteria.stop_words) >= 3
    assert profile.risk_preferences.tolerance == RiskTolerance.MEDIUM
    assert profile.risk_preferences.require_certificates is True
    assert len(profile.certificates) >= 1
    assert profile.metadata["demo_note"] is not None


def test_demo_fixture_categories_are_strings():
    profile = SupplierProfile.load_demo_fixture()
    for cat in profile.criteria.categories:
        assert isinstance(cat, str)
        assert len(cat) > 0


def test_demo_fixture_keywords_and_stop_words_disjoint():
    profile = SupplierProfile.load_demo_fixture()
    keywords_set = set(profile.criteria.keywords)
    stop_words_set = set(profile.criteria.stop_words)
    overlap = keywords_set & stop_words_set
    assert len(overlap) == 0, f"Keywords and stop_words overlap: {overlap}"


def test_demo_fixture_price_range_valid():
    profile = SupplierProfile.load_demo_fixture()
    if profile.criteria.price_min is not None and profile.criteria.price_max is not None:
        assert profile.criteria.price_min < profile.criteria.price_max
        assert profile.criteria.price_min >= 0


def test_demo_fixture_risk_tolerance_enum():
    profile = SupplierProfile.load_demo_fixture()
    assert isinstance(profile.risk_preferences.tolerance, RiskTolerance)


@pytest.mark.parametrize("field", ["supplier_id", "name", "criteria", "risk_preferences"])
def test_demo_fixture_required_fields(field):
    profile = SupplierProfile.load_demo_fixture()
    assert getattr(profile, field) is not None


def test_load_demo_fixture_raises_on_missing_file(monkeypatch):
    import os

    monkeypatch.setattr(os.path, "isfile", lambda _: False)
    with pytest.raises(FileNotFoundError, match="Demo supplier profile fixture not found"):
        SupplierProfile.load_demo_fixture()


def test_supplier_profile_serialization_roundtrip(tmp_path):
    profile = SupplierProfile.load_demo_fixture()
    serialized = profile.model_dump()
    restored = SupplierProfile(**serialized)
    assert restored == profile
    assert restored.supplier_id == profile.supplier_id


def test_supplier_profile_with_full_metadata():
    profile = SupplierProfile(
        supplier_id="full-001",
        name="Full Supplier",
        short_name="FS",
        inn="1234567890",
        description="A full supplier profile",
        criteria=SupplierProfileCriteria(
            categories=["Cat1"],
            regions=["Region1"],
            price_min=5000.0,
            price_max=500000.0,
            keywords=["key1"],
            stop_words=["bad"],
        ),
        risk_preferences=SupplierProfileRiskPreferences(
            tolerance=RiskTolerance.HIGH,
            max_penalty_percent=15.0,
            max_delay_days=90,
            require_certificates=False,
        ),
        certificates=["Cert1"],
        metadata={"key": "value"},
    )
    assert profile.short_name == "FS"
    assert profile.inn == "1234567890"
    assert profile.description == "A full supplier profile"
    assert profile.risk_preferences.tolerance == RiskTolerance.HIGH
    assert profile.risk_preferences.require_certificates is False
    assert profile.certificates == ["Cert1"]
    assert profile.metadata == {"key": "value"}
