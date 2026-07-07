from __future__ import annotations

from src.modules.tender_operator_agent_demo.upload_service import (
    AnalyzedDocument,
    _build_document_grounded_questions,
    _build_document_grounded_requirements,
    _build_preliminary_procurement_analysis,
    _infer_procurement_kind,
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
