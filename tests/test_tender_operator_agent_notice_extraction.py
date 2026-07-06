from src.modules.tender_operator_agent_demo import upload_service as service


def test_goods_preliminary_analysis_reads_nmck_and_delivery_deadline_from_notice():
    analysis = service._build_goods_preliminary_analysis(
        metadata={
            "tender_title": "Поставка электрооборудования",
            "procurement": {"initial_price": 1234567.89},
        },
        technical_spec_text="",
        contract_draft_text="",
        notice_text="""
        Извещение о закупке.
        Срок поставки: в течение 5 рабочих дней с даты заключения контракта.
        """,
    )

    assert "НМЦК: 1 234 567,89 руб." in analysis["overview"]
    assert any("Срок поставки: В течение 5 рабочих дней" in item for item in analysis["overview"])
    assert "НМЦК" in analysis["extracted_fields"]
    assert "срок поставки" in analysis["extracted_fields"]


def test_services_preliminary_analysis_reads_nmck_and_deadline_from_notice_text():
    analysis = service._build_preliminary_procurement_analysis(
        metadata={"tender_title": "Оказание услуг по обучению"},
        technical_spec_text="",
        contract_draft_text="",
        notice_text="""
        Начальная (максимальная) цена контракта: 2 500 000,00 руб.
        Срок оказания услуг: до 30 сентября 2026 года.
        """,
    )

    assert "НМЦК: 2 500 000,00 руб." in analysis["overview"]
    assert any("Срок оказания услуг: до 30 сентября 2026 года" in item for item in analysis["overview"])
    assert "НМЦК" in analysis["extracted_fields"]
    assert "срок оказания услуг" in analysis["extracted_fields"]
