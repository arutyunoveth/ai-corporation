from __future__ import annotations

from src.modules.tender_operator_agent_demo.upload_service import (
    AnalyzedDocument,
    _build_report_markdown,
    _build_document_grounded_questions,
    _build_document_grounded_requirements,
    _build_preliminary_procurement_analysis,
    _infer_procurement_kind,
    _preliminary_analysis_supply_section_markdown,
    _preliminary_analysis_supply_section_title,
)


SOFTWARE_TEXT = """
Выполнение работ по модификации модуля программного комплекса «Здравоохранение»
в части разработки новых структурированных электронных медицинских документов,
обработки информации об ИПРА, интеграции с ЕРН через СМЭВ,
получения данных об участниках СВО с витрины данных Министерства обороны
и передачи лицензии на обновленный модуль.
"""


def test_infer_procurement_kind_detects_mixed_software_integration():
    kind = _infer_procurement_kind(SOFTWARE_TEXT)
    assert kind in {"mixed", "software_modification"}


def test_document_grounded_questions_for_software_procurement_have_no_training_noise():
    questions = _build_document_grounded_questions("mixed", [])
    joined = " ".join(questions).lower()
    assert "преподав" not in joined
    assert "аудитор" not in joined
    assert "обучени" not in joined
    assert any("смэв" in item.lower() for item in questions)
    assert any("лиценз" in item.lower() for item in questions)


def test_document_grounded_requirements_capture_software_blocks():
    documents = [
        AnalyzedDocument(
            display_name="Описание объекта закупки.doc",
            extension=".doc",
            role="technical_spec",
            text=SOFTWARE_TEXT,
            extracted_text_available=True,
            warnings=[],
            source="upload",
            file_id="FILE-01",
            raw_content=None,
        )
    ]
    rows = _build_document_grounded_requirements(documents, "mixed")
    titles = [row["title"] for row in rows]
    assert "Интеграция с ЕРН через СМЭВ" in titles
    assert "Передача лицензии и прав на обновленный модуль" in titles


def test_preliminary_analysis_for_software_procurement_has_work_rows_and_no_training_summary():
    documents = [
        AnalyzedDocument(
            display_name="Описание объекта закупки.doc",
            extension=".doc",
            role="technical_spec",
            text=SOFTWARE_TEXT,
            extracted_text_available=True,
            warnings=[],
            source="upload",
            file_id="FILE-01",
            raw_content=None,
        )
    ]
    result = _build_preliminary_procurement_analysis(
        metadata={"tender_title": "Модификация ПК Здравоохранение", "procurement": {"delivery_term": None}},
        documents=documents,
        technical_spec_text=SOFTWARE_TEXT,
        contract_draft_text="",
        notice_text=SOFTWARE_TEXT,
    )
    assert result["procurement_kind"] in {"mixed", "software_modification"}
    assert result["spec_table"]["rows"]
    summary = " ".join(result["overview"]).lower()
    assert "24 часа" not in summary
    assert "преподав" not in summary


def test_software_preliminary_analysis_supply_section_markdown_uses_work_rows():
    preliminary_analysis = {
        "supply_section_note": "Состав работ собран по техническим документам и проекту контракта.",
        "spec_table": {
            "columns": [
                "№",
                "Блок работ / результат",
                "Что нужно сделать",
                "Входные/внешние системы",
                "Результат для заказчика",
                "Критерии приёмки",
                "Источник",
            ],
            "rows": [
                {
                    "№": "1",
                    "Блок работ / результат": "Интеграция с ЕРН через СМЭВ",
                    "Что нужно сделать": "Настроить обмен данными и интеграционный контур с ЕРН через СМЭВ.",
                    "Входные/внешние системы": "ЕРН, СМЭВ, ПК «Здравоохранение»",
                    "Результат для заказчика": "Рабочая интеграция и обмен данными с внешним регистром",
                    "Критерии приёмки": "Приемка по интеграционному тестированию и доступности обмена",
                    "Источник": "Описание объекта закупки.doc",
                }
            ],
        },
    }

    assert _preliminary_analysis_supply_section_title(preliminary_analysis) == "Состав работ / поставки / услуг"
    markdown = _preliminary_analysis_supply_section_markdown(preliminary_analysis)
    lowered = markdown.lower()
    assert "интеграция с ерн через смэв" in lowered
    assert "что сделать:" in lowered
    assert "системы:" in lowered
    assert "кол-во:" not in lowered


def test_build_report_markdown_for_software_procurement_uses_work_section_heading():
    outputs = {
        "final_recommendation": {
            "recommendation": "manual_review_required",
            "rationale": ["Требуется ручная проверка."],
            "manual_checks": ["Проверить отчет."],
        },
        "quotes_comparison": {"suppliers": []},
        "economics": {"metrics": [{"label": "НМЦК", "value": "12 600 000,00"}]},
        "requirements": {
            "requirements": [],
            "preliminary_analysis": {
                "overview": ["Предмет закупки: модификация ПК «Здравоохранение»."],
                "compliance_highlights": ["Есть интеграции и лицензирование."],
                "contract_highlights": ["Есть условия приемки."],
                "supply_section_note": "Состав работ собран по техническим документам и проекту контракта.",
                "spec_table": {
                    "columns": [
                        "№",
                        "Блок работ / результат",
                        "Что нужно сделать",
                        "Входные/внешние системы",
                        "Результат для заказчика",
                        "Критерии приёмки",
                        "Источник",
                    ],
                    "rows": [
                        {
                            "№": "1",
                            "Блок работ / результат": "Интеграция с ЕРН через СМЭВ",
                            "Что нужно сделать": "Настроить обмен данными и интеграционный контур с ЕРН через СМЭВ.",
                            "Входные/внешние системы": "ЕРН, СМЭВ, ПК «Здравоохранение»",
                            "Результат для заказчика": "Рабочая интеграция и обмен данными с внешним регистром",
                            "Критерии приёмки": "Приемка по интеграционному тестированию и доступности обмена",
                            "Источник": "Описание объекта закупки.doc",
                        }
                    ],
                },
            },
        },
    }
    metadata = {
        "run_id": "toa-run-test",
        "tender_title": "Модификация ПК «Здравоохранение»",
        "tender_category": "44-ФЗ",
        "customer_name": "Тестовый заказчик",
        "status": "needs_review",
        "analysis_mode": "fallback_deterministic_adapter",
    }

    markdown = _build_report_markdown(metadata, outputs)
    lowered = markdown.lower()
    assert "## состав работ / поставки / услуг" in lowered
    assert "интеграция с ерн через смэв" in lowered
    assert "кол-во:" not in lowered
