from pathlib import Path


PRODUCT_DIR = Path("docs/product")
SAMPLES_DIR = PRODUCT_DIR / "samples"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_controlled_pilot_sales_materials_exist_and_keep_controlled_positioning():
    one_pager = _read(PRODUCT_DIR / "Sales_One_Pager_MVP_v1.md")
    offer = _read(PRODUCT_DIR / "Pilot_Offer_Description.md")
    limitations = _read(PRODUCT_DIR / "Pilot_Limitations_Disclosure.md")
    pricing = _read(PRODUCT_DIR / "Pricing_Test_Menu.md")

    assert "operator-assisted" in one_pager
    assert "no autonomous bid submission" in one_pager
    assert "human submission" in limitations
    assert "no legal guarantee" in limitations
    assert "no autonomous platform action" in limitations
    assert "no supplier outreach without explicit human approval" in limitations
    assert "controlled LLM mode optional" in offer
    assert "not billing automation" in pricing


def test_sample_customer_reports_include_pilot_disclosures():
    base_sample = _read(SAMPLES_DIR / "Commercial_MVP_v1_Sample_Customer_Report.md")
    pilot_sample = _read(SAMPLES_DIR / "Controlled_Pilot_CP_SC_004_Customer_Report.md")

    for text in [base_sample, pilot_sample]:
        assert "human submission only" in text
        assert "no legal guarantee" in text
        assert "no autonomous platform action" in text
        assert "no supplier outreach without approval" in text
