from __future__ import annotations

from src.modules.tender_operator_agent_demo.eis_notice_parser import (
    extract_notice_attachments,
    extract_notice_metadata,
    merge_structured_metadata,
    build_notice_priority_prompt_section,
    apply_structured_metadata_to_procurement,
)


SAMPLE_XML_44FZ = """<?xml version="1.0" encoding="UTF-8"?>
<epNotification xmlns="http://zakupki.gov.ru/223fz/epNotification/11"
                xmlns:ns2="http://zakupki.gov.ru/223fz/types/1"
                xmlns:ns3="http://zakupki.gov.ru/223fz/reference/1"
                xmlns:ns4="http://zakupki.gov.ru/223fz/epNotification/12">
  <ns4:maxPrice>5000000.00</ns4:maxPrice>
  <ns4:publishDate>2026-07-01T14:30:00</ns4:publishDate>
  <ns4:endDate>2026-07-15T12:00:00</ns4:endDate>
  <ns4:deliveryTerm>до 31.12.2026</ns4:deliveryTerm>
  <ns4:placer>
    <ns4:inn>7712345678</ns4:inn>
    <ns4:fullName>Федеральное казённое учреждение</ns4:fullName>
  </ns4:placer>
  <ns4:procedureType>Электронный аукцион</ns4:procedureType>
</epNotification>
"""

SAMPLE_XML_ALT_NS = """<?xml version="1.0" encoding="UTF-8"?>
<epNotification xmlns:ns6="http://zakupki.gov.ru/223fz/epNotification/12"
                xmlns:ns7="http://zakupki.gov.ru/223fz/types/1">
  <ns6:initialPrice>1500000.00</ns6:initialPrice>
  <ns6:placingDate>2026-06-15T10:00:00</ns6:placingDate>
  <ns6:collectingEndDate>2026-07-01T10:00:00</ns6:collectingEndDate>
  <ns6:deliveryTermInfo>в течение 60 дней с даты подписания</ns6:deliveryTermInfo>
  <ns6:customerInfo>
    <ns6:inn>7722334455</ns6:inn>
    <ns6:fullName>ГБУ Здравоохранения</ns6:fullName>
  </ns6:customerInfo>
  <ns6:lotSubject>Поставка медицинского оборудования</ns6:lotSubject>
  <ns6:purchaseMethod>Запрос котировок</ns6:purchaseMethod>
</epNotification>
"""

SAMPLE_XML_NO_NS = """<?xml version="1.0" encoding="UTF-8"?>
<epNotification>
  <maxPrice>2500000.00</maxPrice>
  <publishDate>2026-05-01T09:00:00</publishDate>
  <applicationEndDate>2026-05-20T09:00:00</applicationEndDate>
  <deliveryTerm>30 дней</deliveryTerm>
  <customer>
    <fullName>АО Рога и Копыта</fullName>
    <inn>7711223344</inn>
  </customer>
  <subject>Услуги по уборке</subject>
</epNotification>
"""

SAMPLE_XML_WITH_ATTACHMENTS = """<?xml version="1.0" encoding="UTF-8"?>
<epNotification xmlns="http://zakupki.gov.ru/44fz/types/1">
  <attachmentsInfo>
    <attachmentInfo>
      <fileName>Описание объекта закупки.docx</fileName>
      <url>https://zakupki.gov.ru/44fz/filestore/public/1.0/download/priz/file.html?uid=uid-001</url>
    </attachmentInfo>
    <attachmentInfo>
      <fileName>Проект контракта.docx</fileName>
      <url>https://zakupki.gov.ru/44fz/filestore/public/1.0/download/priz/file.html?uid=uid-002</url>
    </attachmentInfo>
  </attachmentsInfo>
</epNotification>
"""


class TestExtractNoticeMetadata:
    def test_extracts_44fz_notice_with_namespace(self):
        result = extract_notice_metadata(SAMPLE_XML_44FZ)
        assert result.get("_has_notice_data") is True
        assert result.get("nmck") == 5000000.0
        assert result.get("publication_date") == "01.07.2026"
        assert result.get("submission_deadline") == "15.07.2026"
        assert result.get("delivery_term") == "до 31.12.2026"
        assert result.get("customer_name") == "Федеральное казённое учреждение"
        assert result.get("customer_inn") == "7712345678"
        assert result.get("procedure_type") == "Электронный аукцион"
        assert result.get("source_label") == "электронное извещение ЕИС"

    def test_extracts_alt_namespace_notice(self):
        result = extract_notice_metadata(SAMPLE_XML_ALT_NS)
        assert result.get("_has_notice_data") is True
        assert result.get("nmck") == 1500000.0
        assert result.get("publication_date") == "15.06.2026"
        assert result.get("submission_deadline") == "01.07.2026"
        assert result.get("delivery_term") == "в течение 60 дней с даты подписания"
        assert result.get("customer_name") == "ГБУ Здравоохранения"
        assert result.get("customer_inn") == "7722334455"
        assert result.get("procurement_subject") == "Поставка медицинского оборудования"
        assert result.get("procedure_type") == "Запрос котировок"

    def test_extracts_no_namespace_notice(self):
        result = extract_notice_metadata(SAMPLE_XML_NO_NS)
        assert result.get("_has_notice_data") is True
        assert result.get("nmck") == 2500000.0
        assert result.get("publication_date") == "01.05.2026"
        assert result.get("submission_deadline") == "20.05.2026"
        assert result.get("delivery_term") == "30 дней"
        assert result.get("customer_name") == "АО Рога и Копыта"
        assert result.get("customer_inn") == "7711223344"

    def test_returns_empty_on_invalid_xml(self):
        result = extract_notice_metadata("not xml at all")
        assert result == {}

    def test_returns_empty_on_empty_input(self):
        result = extract_notice_metadata("")
        assert result == {}
        result = extract_notice_metadata(None)
        assert result == {}

    def test_extracts_attachment_links_from_notice_xml(self):
        result = extract_notice_attachments(SAMPLE_XML_WITH_ATTACHMENTS)
        assert len(result) == 2
        assert result[0]["name"] == "Описание объекта закупки.docx"
        assert result[0]["document_kind"] == "procurement_object_description"
        assert result[1]["document_kind"] == "contract_draft"


class TestMergeStructuredMetadata:
    def test_notice_priority_over_card_and_docs(self):
        notice = {"nmck": 5000000.0, "publication_date": "01.07.2026", "_has_notice_data": True}
        card = {"nmck": 4800000.0, "publication_date": "30.06.2026"}
        doc = {"nmck": 5100000.0}
        result = merge_structured_metadata(notice, card, doc)
        assert result["initial_price"]["value"] == 5000000.0
        assert result["initial_price"]["source"] == "eis_notice"
        assert result["publication_date"]["value"] == "01.07.2026"
        assert result["publication_date"]["source"] == "eis_notice"

    def test_card_fallback_when_no_notice(self):
        notice = {}
        card = {"nmck": 4800000.0, "publication_date": "30.06.2026"}
        doc = {}
        result = merge_structured_metadata(notice, card, doc)
        assert result["initial_price"]["value"] == 4800000.0
        assert result["initial_price"]["source"] == "card"
        assert result["publication_date"]["value"] == "30.06.2026"

    def test_doc_fallback_when_no_notice_no_card(self):
        notice = {}
        card = {}
        doc = {"customer_name": "Документ заказчик"}
        result = merge_structured_metadata(notice, card, doc)
        assert result["customer_name"]["value"] == "Документ заказчик"
        assert result["customer_name"]["source"] == "documents"

    def test_apply_to_procurement(self):
        structured = {
            "initial_price": {"value": 5000000.0, "source": "eis_notice", "source_label": "электронное извещение ЕИС"},
            "publication_date": {"value": "01.07.2026", "source": "eis_notice", "source_label": "электронное извещение ЕИС"},
            "deadline": {"value": "15.07.2026", "source": "eis_notice", "source_label": "электронное извещение ЕИС"},
        }
        procurement: dict = {}
        apply_structured_metadata_to_procurement(procurement, structured)
        assert procurement["initial_price"] == 5000000.0
        assert procurement["publication_date"] == "01.07.2026"
        assert procurement["deadline"] == "15.07.2026"
        assert "электронное извещение ЕИС" in procurement.get("structured_source_label", "")


class TestBuildNoticePriorityPromptSection:
    def test_builds_section_with_data(self):
        procurement = {
            "initial_price": 5000000.0,
            "publication_date": "01.07.2026",
            "deadline": "15.07.2026",
            "structured_source_label": "электронное извещение ЕИС",
        }
        section = build_notice_priority_prompt_section(procurement)
        assert "НМЦК: 5000000.0" in section
        assert "01.07.2026" in section
        assert "15.07.2026" in section
        assert "электронное извещение ЕИС" in section
        assert "Instruction:" in section

    def test_builds_section_with_minimal_data(self):
        procurement = {"structured_source_label": "карточка ЕИС"}
        section = build_notice_priority_prompt_section(procurement)
        assert "карточка ЕИС" in section
        assert "Instruction:" in section
