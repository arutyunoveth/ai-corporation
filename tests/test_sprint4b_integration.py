from src.modules.ceo_approval.models import CEOApprovalCondition, CEOApprovalRecord, CEOApprovalSet
from src.modules.contract_risks.models import ContractRiskFlag, ContractRiskRecord, ContractRiskSet
from src.modules.event_log.models import DecisionRecord, EventRecord
from src.modules.integrated_risk_memo.models import (
    IntegratedRiskItem,
    IntegratedRiskMemoRecord,
    IntegratedRiskMemoSet,
)
from tests.test_sprint3b_integration import _build_analysis_package, _create_artifact, _create_supplier


def _prepare_risk_approval_prerequisites(client):
    intake, document_set, summary, matrix, requirements, risks = _build_analysis_package(client)

    first = _create_supplier(
        client, legal_name="ООО ЭлектроСнаб", display_name="ЭлектроСнаб", inn="7702234567"
    )
    second = _create_supplier(
        client, legal_name="ООО КабельИмпорт", display_name="КабельИмпорт", inn="7702234568"
    )

    client.post(
        f"/suppliers/{first['supplier_id']}/contacts",
        json={"contact_name": "Иван Петров", "email": "sales@electro.example", "is_primary": True},
    )
    client.post(f"/suppliers/{first['supplier_id']}/tags", json={"tag_code": "ELECTRICAL_EQUIPMENT"})
    client.post(f"/suppliers/{first['supplier_id']}/tags", json={"tag_code": "TENDER_READY"})
    client.post(
        f"/suppliers/{second['supplier_id']}/contacts",
        json={"contact_name": "Ольга Смирнова", "email": "quotes@cable.example", "is_primary": True},
    )

    shortlist = client.post(
        "/supplier-search/build",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
            "compliance_matrix_id": matrix["compliance_matrix_id"],
            "document_requirement_set_id": requirements["document_requirement_set_id"],
            "risk_flag_set_id": risks["risk_flag_set_id"],
        },
    ).json()
    rfq_batch = client.post(
        "/rfq/batches/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    ).json()
    communication_set = client.post(
        "/supplier-communications/sets/build",
        json={"deal_id": intake["deal_id"], "rfq_batch_id": rfq_batch["rfq_batch_id"]},
    ).json()

    for thread in communication_set["threads"]:
        client.post(
            f"/supplier-communications/threads/{thread['supplier_thread_id']}/messages",
            json={
                "direction": "OUTBOUND",
                "message_subject": "Запрос ТКП",
                "message_text": "Просим направить коммерческое предложение.",
            },
        )

    for index, thread in enumerate(communication_set["threads"], start=1):
        quote_artifact = _create_artifact(
            client,
            intake["deal_id"],
            f"quote-risk-{index}.pdf",
            artifact_type="SUPPLIER_QUOTE",
        )
        client.post(
            "/quotes/register",
            json={
                "deal_id": intake["deal_id"],
                "supplier_id": thread["supplier_id"],
                "rfq_id": thread["rfq_id"],
                "supplier_thread_id": thread["supplier_thread_id"],
                "quoted_amount": 125000.0 + index * 5000,
                "currency_code": "RUB",
                "notes": f"Quote {index}",
                "artifact_refs": [quote_artifact["artifact_ref"]],
            },
        )

    quote_set_id = client.get("/quotes", params={"deal_id": intake["deal_id"]}).json()[0]["quote_set_id"]
    verification = client.post(
        "/supplier-verification/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    ).json()
    comparison = client.post(
        "/quote-comparison/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_set_id": quote_set_id,
            "supplier_verification_set_id": verification["supplier_verification_set_id"],
        },
    ).json()
    cost_model = client.post(
        "/cost-model/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_comparison_set_id": comparison["quote_comparison_set_id"],
        },
    ).json()
    cash_gap = client.post(
        "/cash-gap/build",
        json={"deal_id": intake["deal_id"], "cost_model_set_id": cost_model["cost_model_set_id"]},
    ).json()
    financing = client.post(
        "/financing-strategy/build",
        json={"deal_id": intake["deal_id"], "cash_gap_set_id": cash_gap["cash_gap_set_id"]},
    ).json()
    finance_memo = client.post(
        "/finance-memo/build",
        json={
            "deal_id": intake["deal_id"],
            "cost_model_set_id": cost_model["cost_model_set_id"],
            "cash_gap_set_id": cash_gap["cash_gap_set_id"],
            "financing_strategy_set_id": financing["financing_strategy_set_id"],
        },
    ).json()
    return {
        "intake": intake,
        "document_set": document_set,
        "summary": summary,
        "matrix": matrix,
        "requirements": requirements,
        "risks": risks,
        "shortlist": shortlist,
        "verification": verification,
        "comparison": comparison,
        "cost_model": cost_model,
        "cash_gap": cash_gap,
        "financing": financing,
        "finance_memo": finance_memo,
    }


def test_build_contract_risk_and_persist_records_flags(client, session):
    package = _prepare_risk_approval_prerequisites(client)
    response = client.post(
        "/contract-risks/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_set_id": package["document_set"]["document_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    risk_set = session.query(ContractRiskSet).filter_by(contract_risk_set_id=payload["contract_risk_set_id"]).one()
    records = session.query(ContractRiskRecord).filter_by(contract_risk_set_id=payload["contract_risk_set_id"]).all()
    flags = session.query(ContractRiskFlag).join(
        ContractRiskRecord,
        ContractRiskRecord.contract_risk_id == ContractRiskFlag.contract_risk_id,
    ).filter(ContractRiskRecord.contract_risk_set_id == payload["contract_risk_set_id"]).all()

    assert risk_set.deal_id == package["intake"]["deal_id"]
    assert len(records) >= 1
    assert len(flags) >= 1


def test_build_integrated_risk_memo_and_persist_items_recommendation(client, session):
    package = _prepare_risk_approval_prerequisites(client)
    contract_risks = client.post(
        "/contract-risks/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_set_id": package["document_set"]["document_set_id"],
        },
    ).json()

    response = client.post(
        "/integrated-risk-memo/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "initial_tech_risk_flag_set_id": package["risks"]["risk_flag_set_id"],
            "supplier_verification_set_id": package["verification"]["supplier_verification_set_id"],
            "quote_comparison_set_id": package["comparison"]["quote_comparison_set_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "contract_risk_set_id": contract_risks["contract_risk_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    memo_set = session.query(IntegratedRiskMemoSet).filter_by(
        integrated_risk_memo_set_id=payload["integrated_risk_memo_set_id"]
    ).one()
    record = session.query(IntegratedRiskMemoRecord).filter_by(
        integrated_risk_memo_set_id=payload["integrated_risk_memo_set_id"]
    ).one()
    items = session.query(IntegratedRiskItem).filter_by(integrated_risk_memo_id=record.integrated_risk_memo_id).all()

    assert memo_set.deal_id == package["intake"]["deal_id"]
    assert record.recommendation in {"GO", "GO_WITH_CONDITIONS", "NO_GO", "NEEDS_REVIEW"}
    assert len(items) >= 1


def test_build_ceo_approval_and_record_decision_conditions(client, session):
    package = _prepare_risk_approval_prerequisites(client)
    contract_risks = client.post(
        "/contract-risks/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_set_id": package["document_set"]["document_set_id"],
        },
    ).json()
    integrated_memo = client.post(
        "/integrated-risk-memo/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "initial_tech_risk_flag_set_id": package["risks"]["risk_flag_set_id"],
            "supplier_verification_set_id": package["verification"]["supplier_verification_set_id"],
            "quote_comparison_set_id": package["comparison"]["quote_comparison_set_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "contract_risk_set_id": contract_risks["contract_risk_set_id"],
        },
    ).json()
    approval_set = client.post(
        "/ceo-approval/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "integrated_risk_memo_set_id": integrated_memo["integrated_risk_memo_set_id"],
        },
    ).json()

    response = client.post(
        "/ceo-approval/decide",
        json={
            "ceo_approval_set_id": approval_set["ceo_approval_set_id"],
            "decision": "GO_WITH_CONDITIONS",
            "decided_by_ref": "CEO",
            "rationale": "Финансово приемлемо при выполнении контрольных условий.",
            "conditions": [
                {
                    "condition_code": "ALT_SUPPLIER_BACKUP",
                    "condition_text": "Подтвердить резервного поставщика до старта bid prep",
                }
            ],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    approval = session.query(CEOApprovalSet).filter_by(ceo_approval_set_id=approval_set["ceo_approval_set_id"]).one()
    record = session.query(CEOApprovalRecord).filter_by(ceo_approval_id=payload["ceo_approval_id"]).one()
    conditions = session.query(CEOApprovalCondition).filter_by(ceo_approval_id=payload["ceo_approval_id"]).all()

    assert approval.deal_id == package["intake"]["deal_id"]
    assert approval.approval_status == "DECIDED"
    assert record.decision == "GO_WITH_CONDITIONS"
    assert len(conditions) == 1


def test_sprint4b_outputs_linked_to_deal_and_events_written(client, session):
    package = _prepare_risk_approval_prerequisites(client)
    contract_risks = client.post(
        "/contract-risks/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_set_id": package["document_set"]["document_set_id"],
        },
    ).json()
    integrated_memo = client.post(
        "/integrated-risk-memo/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "initial_tech_risk_flag_set_id": package["risks"]["risk_flag_set_id"],
            "supplier_verification_set_id": package["verification"]["supplier_verification_set_id"],
            "quote_comparison_set_id": package["comparison"]["quote_comparison_set_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "contract_risk_set_id": contract_risks["contract_risk_set_id"],
        },
    ).json()
    approval_set = client.post(
        "/ceo-approval/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "integrated_risk_memo_set_id": integrated_memo["integrated_risk_memo_set_id"],
        },
    ).json()
    decision = client.post(
        "/ceo-approval/decide",
        json={
            "ceo_approval_set_id": approval_set["ceo_approval_set_id"],
            "decision": "GO",
            "decided_by_ref": "CEO",
            "rationale": "Можно продолжать подготовку заявки.",
            "conditions": [],
        },
    ).json()

    assert session.query(ContractRiskSet).filter_by(
        contract_risk_set_id=contract_risks["contract_risk_set_id"], deal_id=package["intake"]["deal_id"]
    ).count() == 1
    assert session.query(IntegratedRiskMemoSet).filter_by(
        integrated_risk_memo_set_id=integrated_memo["integrated_risk_memo_set_id"],
        deal_id=package["intake"]["deal_id"],
    ).count() == 1
    assert session.query(CEOApprovalSet).filter_by(
        ceo_approval_set_id=approval_set["ceo_approval_set_id"], deal_id=package["intake"]["deal_id"]
    ).count() == 1
    assert session.query(DecisionRecord).filter_by(deal_id=package["intake"]["deal_id"], decision_code="CEO_APPROVAL_DECISION").count() == 1

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=package["intake"]["deal_id"]).all()}
    assert "contract_risk_build_started" in event_codes
    assert "contract_risk_built" in event_codes
    assert "integrated_risk_memo_build_started" in event_codes
    assert "integrated_risk_memo_built" in event_codes
    assert "ceo_approval_package_built" in event_codes
    assert "ceo_decision_recorded" in event_codes
    assert decision["decision"] == "GO"


def test_sprint4b_reruns_are_append_only(client, session):
    package = _prepare_risk_approval_prerequisites(client)
    first_contract = client.post(
        "/contract-risks/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_set_id": package["document_set"]["document_set_id"],
        },
    ).json()
    second_contract = client.post(
        "/contract-risks/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_set_id": package["document_set"]["document_set_id"],
        },
    ).json()
    assert first_contract["contract_risk_set_id"] != second_contract["contract_risk_set_id"]

    first_memo = client.post(
        "/integrated-risk-memo/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "initial_tech_risk_flag_set_id": package["risks"]["risk_flag_set_id"],
            "supplier_verification_set_id": package["verification"]["supplier_verification_set_id"],
            "quote_comparison_set_id": package["comparison"]["quote_comparison_set_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "contract_risk_set_id": first_contract["contract_risk_set_id"],
        },
    ).json()
    second_memo = client.post(
        "/integrated-risk-memo/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "initial_tech_risk_flag_set_id": package["risks"]["risk_flag_set_id"],
            "supplier_verification_set_id": package["verification"]["supplier_verification_set_id"],
            "quote_comparison_set_id": package["comparison"]["quote_comparison_set_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "contract_risk_set_id": second_contract["contract_risk_set_id"],
        },
    ).json()
    assert first_memo["integrated_risk_memo_set_id"] != second_memo["integrated_risk_memo_set_id"]

    approval_set = client.post(
        "/ceo-approval/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "integrated_risk_memo_set_id": first_memo["integrated_risk_memo_set_id"],
        },
    ).json()
    first_decision = client.post(
        "/ceo-approval/decide",
        json={
            "ceo_approval_set_id": approval_set["ceo_approval_set_id"],
            "decision": "NEEDS_REVIEW",
            "decided_by_ref": "CEO",
            "rationale": "Нужен дополнительный просмотр рисков.",
            "conditions": [],
        },
    ).json()
    second_decision = client.post(
        "/ceo-approval/decide",
        json={
            "ceo_approval_set_id": approval_set["ceo_approval_set_id"],
            "decision": "GO",
            "decided_by_ref": "CEO",
            "rationale": "Риски приняты, можно идти дальше.",
            "conditions": [],
        },
    ).json()

    assert first_decision["ceo_approval_id"] != second_decision["ceo_approval_id"]
    assert session.query(CEOApprovalRecord).filter_by(ceo_approval_set_id=approval_set["ceo_approval_set_id"]).count() == 2
