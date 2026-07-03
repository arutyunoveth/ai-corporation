from src.modules.controlled_llm_prebid import service as controlled_llm_service
from src.modules.controlled_llm_prebid.service import run_controlled_tender_operator_workflow
from src.modules.runtime_control_traces.models import RuntimeControlTrace
from src.shared.config.settings import get_settings


def test_controlled_tender_operator_stub_workflow_returns_structured_artifacts_and_traces(session):
    result = run_controlled_tender_operator_workflow(
        session,
        provider_mode="stub",
        context={
            "deal_id": "PP1R-TEST-001",
            "operator_id": "tender_operator_001",
            "operator_profile": {"found": True, "has_margin_info": True},
            "documents": {
                "notice_text": "Synthetic Notice\nSupply and installation of electrical equipment.",
                "technical_spec_text": "Synthetic technical specification with warranty and delivery terms.",
                "contract_draft_text": "Synthetic contract draft with penalties, security, and acceptance clauses.",
            },
            "tkp_inputs": [
                {
                    "supplier_label": "supplier_alpha",
                    "source_file": "/tmp/supplier_alpha.txt",
                    "quote_text": "Synthetic quote with delivery in 20 days and price information.",
                }
            ],
        },
        include_quote_normalization=True,
        include_bid_decision=True,
    )

    assert result.analysis_mode == "llm_tender_operator_stub"
    assert result.overall_review_status == "needs_human_review"
    assert result.requirements["technical_requirements"]
    assert result.supplier_questions[0]["question"]
    assert result.rfq_draft["email_subject"]
    assert result.contract_risks[0]["classification"] in {
        "market_standard_harsh_term",
        "commercially_material_risk",
        "deal_breaker_candidate",
    }
    assert result.quote_normalization is not None
    assert result.quote_normalization["quotes"][0]["supplier_label"] == "supplier_alpha"
    assert result.bid_decision is not None
    assert result.bid_decision["preliminary_recommendation"] == "NEEDS_REVIEW"

    traces = session.query(RuntimeControlTrace).filter(RuntimeControlTrace.runtime_trace_id.in_(result.trace_ids)).all()
    assert len(traces) == 6
    assert all(trace.prompt_schema_ref for trace in traces)
    assert all(trace.agent_profile_ref for trace in traces)


def test_controlled_tender_operator_llm_path_redacts_inputs_and_does_not_store_raw_by_default(session, monkeypatch):
    monkeypatch.setenv("AI_CORP_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_CORP_LLM_MODEL", "test-model")
    monkeypatch.setenv("AI_CORP_OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("AI_CORP_LLM_ALLOW_RAW_PARTNER_DATA", raising=False)
    monkeypatch.delenv("AI_CORP_LLM_STORE_RAW_RESPONSE", raising=False)
    get_settings.cache_clear()

    class _FakeProvider:
        provider_name = "openai_compatible"

        def generate(self, section, context, prompt_record):
            notice_text = context["documents"]["notice_text"]
            assert "[REDACTED_EMAIL]" in notice_text
            assert "[REDACTED_PHONE]" in notice_text
            if section == "requirements":
                return {
                    "tender_summary": "Sanitized summary",
                    "technical_requirements": ["Requirement A"],
                    "qualification_requirements": ["Qualification A"],
                    "document_requirements": ["Document A"],
                    "evaluation_criteria": ["Price"],
                    "procurement_categories": ["Equipment"],
                }
            if section == "supplier_questions":
                return {"supplier_questions": [{"question": "Question?", "category": "general"}]}
            if section == "rfq_draft":
                return {
                    "email_subject": "RFQ",
                    "intro": "Manual review only",
                    "requirements_summary": ["Requirement A"],
                    "supplier_questions": ["Question?"],
                    "requested_response_items": ["TKP"],
                    "commercial_terms": ["VAT"],
                    "closing_note": "Human review required",
                }
            if section == "contract_risk_memo":
                return {
                    "contract_risks": [
                        {
                            "clause": "Clause A",
                            "description": "Desc",
                            "classification": "commercially_material_risk",
                            "impact": "Impact",
                            "mitigation": "Mitigation",
                            "operator_decision_required": True,
                        }
                    ]
                }
            raise AssertionError(f"Unexpected section: {section}")

    monkeypatch.setattr(controlled_llm_service, "_build_provider_from_settings", lambda settings, provider_name_override=None: _FakeProvider())

    result = run_controlled_tender_operator_workflow(
        session,
        provider_mode="llm",
        context={
            "deal_id": "PP1R-TEST-002",
            "operator_id": "tender_operator_001",
            "documents": {
                "notice_text": "Contact john@example.com or +7 999 111 22 33 for tender details.",
                "technical_spec_text": "Spec line",
                "contract_draft_text": "Contract line 123456789012",
            },
            "tkp_inputs": [],
        },
        include_quote_normalization=False,
        include_bid_decision=False,
    )

    assert result.resolved_provider == "openai_compatible"
    requirements_section = result.sections["requirements"]
    assert requirements_section["raw_output"] is None
    assert requirements_section["input_redaction"]["redaction_applied"] is True
    assert requirements_section["input_redaction"]["input_chars_before"] != requirements_section["input_redaction"]["input_chars_after"]

    traces = session.query(RuntimeControlTrace).filter(RuntimeControlTrace.runtime_trace_id.in_(result.trace_ids)).all()
    assert traces
    assert all("redaction_applied=true" in trace.input_summary for trace in traces)
    assert all("input_chars_before=" in trace.input_summary for trace in traces)
    assert all("raw_response_stored" in trace.output_summary for trace in traces)

    get_settings.cache_clear()
