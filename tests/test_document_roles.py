from __future__ import annotations

import inspect

import pytest

from src.modules.customer_pilot import input_resolver
from src.modules.procurement_analysis.document_roles import detect_document_role


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("EPNotification.xml", "notice"),
        ("ПРОТОКОЛ_РАССМОТРЕНИЯ.XML", "notice"),
        ("Техническое задание.docx", "technical_spec"),
        ("Technical specification.pdf", "technical_spec"),
        ("Спецификация.xlsx", "technical_spec"),
        ("Проект договора.docx", "contract_draft"),
        ("Commercial proposal.pdf", "tkp"),
        ("Коммерческое предложение.pdf", "tkp"),
        ("Извещение о закупке.pdf", "notice"),
        ("readme.txt", "supporting"),
    ],
)
def test_document_role_policy_is_neutral_and_multilingual(name: str, expected: str):
    assert detect_document_role(name) == expected


def test_customer_input_resolver_has_no_demo_module_dependency():
    assert "tender_operator_agent_demo" not in inspect.getsource(input_resolver)
