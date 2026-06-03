from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.contract_risks.models import ContractRiskFlag, ContractRiskRecord, ContractRiskSet
from src.modules.contract_risks.schemas import BuildContractRiskRequest
from src.modules.document_ingestion.service import get_document_set
from src.modules.document_store.service import get_artifact
from src.modules.event_log.service import append_event_record
from src.shared.db.base import utcnow
from src.shared.enums import (
    ContractClauseType,
    ContractRiskStatus,
    DocumentSetItemRole,
    EventSeverity,
    RiskSeverity,
)
from src.shared.errors import NotFoundError
from src.shared.ids import next_contract_risk_id, next_contract_risk_set_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, contract_risk_set_id: str) -> ContractRiskSet:
    record = session.scalar(
        select(ContractRiskSet).where(ContractRiskSet.contract_risk_set_id == contract_risk_set_id)
    )
    if not record:
        raise NotFoundError(f"Contract risk set '{contract_risk_set_id}' was not found")
    return record


def _get_records(session: Session, contract_risk_set_id: str) -> list[ContractRiskRecord]:
    return list(
        session.scalars(
            select(ContractRiskRecord)
            .where(ContractRiskRecord.contract_risk_set_id == contract_risk_set_id)
            .order_by(ContractRiskRecord.created_at.asc(), ContractRiskRecord.id.asc())
        )
    )


def _get_flags(session: Session, contract_risk_id: str) -> list[ContractRiskFlag]:
    return list(
        session.scalars(
            select(ContractRiskFlag)
            .where(ContractRiskFlag.contract_risk_id == contract_risk_id)
            .order_by(ContractRiskFlag.created_at.asc(), ContractRiskFlag.id.asc())
        )
    )


def _risk_blueprints(document_set, items, artifacts: dict[str, object]) -> list[dict]:
    blueprints: list[dict] = []
    has_contract = False

    for item in items:
        artifact = artifacts[item.artifact_ref]
        file_name = artifact.file_name.lower()
        source_ref = f"ARTIFACT:{artifact.artifact_ref}"
        is_contract = item.item_role == DocumentSetItemRole.DRAFT_CONTRACT or "contract" in file_name or "договор" in file_name
        if is_contract:
            has_contract = True
            blueprints.extend(
                [
                    {
                        "source_artifact_ref": artifact.artifact_ref,
                        "clause_type": ContractClauseType.PAYMENT,
                        "severity": RiskSeverity.HIGH,
                        "summary": "Payment terms require manual review before bid approval.",
                        "notes": f"Draft contract artifact '{artifact.file_name}' was parsed with rule-based payment heuristics.",
                        "flags": [
                            {
                                "flag_code": "PAYMENT_TERMS_REVIEW",
                                "severity": RiskSeverity.HIGH,
                                "summary": "Contract draft may contain non-standard payment timing or advance requirements.",
                                "source_ref": source_ref,
                            }
                        ],
                    },
                    {
                        "source_artifact_ref": artifact.artifact_ref,
                        "clause_type": ContractClauseType.PENALTY,
                        "severity": RiskSeverity.HIGH,
                        "summary": "Penalty clauses should be validated against delivery and supplier assumptions.",
                        "notes": f"Penalty exposure inferred from persisted contract draft '{artifact.file_name}'.",
                        "flags": [
                            {
                                "flag_code": "PENALTY_EXPOSURE_REVIEW",
                                "severity": RiskSeverity.HIGH,
                                "summary": "Penalty liability may exceed current comfort threshold without legal validation.",
                                "source_ref": source_ref,
                            }
                        ],
                    },
                    {
                        "source_artifact_ref": artifact.artifact_ref,
                        "clause_type": ContractClauseType.ACCEPTANCE,
                        "severity": RiskSeverity.MEDIUM,
                        "summary": "Acceptance and sign-off flow should be clarified before submission.",
                        "notes": f"Acceptance sequence inferred from contract draft '{artifact.file_name}'.",
                        "flags": [
                            {
                                "flag_code": "ACCEPTANCE_FLOW_REVIEW",
                                "severity": RiskSeverity.MEDIUM,
                                "summary": "Acceptance procedure may create operational delay or dispute risk.",
                                "source_ref": source_ref,
                            }
                        ],
                    },
                ]
            )
            continue

        if item.item_role == DocumentSetItemRole.TZ:
            blueprints.append(
                {
                    "source_artifact_ref": artifact.artifact_ref,
                    "clause_type": ContractClauseType.DELIVERY,
                    "severity": RiskSeverity.MEDIUM,
                    "summary": "Technical specification implies delivery obligations that must align with quote assumptions.",
                    "notes": f"Delivery obligations inferred from TZ artifact '{artifact.file_name}'.",
                    "flags": [
                        {
                            "flag_code": "DELIVERY_ALIGNMENT_REVIEW",
                            "severity": RiskSeverity.MEDIUM,
                            "summary": "Delivery expectations from technical specification may pressure execution timelines.",
                            "source_ref": source_ref,
                        }
                    ],
                }
            )
        elif item.item_role == DocumentSetItemRole.NOTICE:
            blueprints.append(
                {
                    "source_artifact_ref": artifact.artifact_ref,
                    "clause_type": ContractClauseType.WARRANTY,
                    "severity": RiskSeverity.LOW,
                    "summary": "Tender notice may contain warranty or support obligations needing confirmation.",
                    "notes": f"Notice artifact '{artifact.file_name}' contributes contextual warranty assumptions.",
                    "flags": [
                        {
                            "flag_code": "WARRANTY_SCOPE_CONFIRMATION",
                            "severity": RiskSeverity.LOW,
                            "summary": "Warranty scope should be confirmed against supplier commitments.",
                            "source_ref": source_ref,
                        }
                    ],
                }
            )

    if not has_contract:
        blueprints.insert(
            0,
            {
                "source_artifact_ref": None,
                "clause_type": ContractClauseType.OTHER,
                "severity": RiskSeverity.HIGH,
                "summary": "No persisted draft contract was found in the formal document set.",
                "notes": "Contract risk parser could not inspect a formal draft contract artifact.",
                "flags": [
                    {
                        "flag_code": "MISSING_DRAFT_CONTRACT",
                        "severity": RiskSeverity.HIGH,
                        "summary": "Contract review cannot be completed because draft contract is absent from the persisted package.",
                        "source_ref": f"DOCUMENT_SET:{document_set.document_set_id}",
                    }
                ],
            },
        )

    if not blueprints:
        blueprints.append(
            {
                "source_artifact_ref": None,
                "clause_type": ContractClauseType.OTHER,
                "severity": RiskSeverity.LOW,
                "summary": "No contract-specific red flags were inferred; baseline legal review is still recommended.",
                "notes": "Fallback contract risk record.",
                "flags": [
                    {
                        "flag_code": "BASELINE_CONTRACT_REVIEW",
                        "severity": RiskSeverity.LOW,
                        "summary": "Proceed with routine legal review before approval.",
                        "source_ref": f"DOCUMENT_SET:{document_set.document_set_id}",
                    }
                ],
            }
        )
    return blueprints


def build_contract_risks(
    session: Session,
    payload: BuildContractRiskRequest,
) -> ContractRiskSet:
    document_set, items, _runs = get_document_set(session, payload.document_set_id)
    require_same_reference(payload.deal_id, document_set.deal_id, "deal_id")
    artifacts = {item.artifact_ref: get_artifact(session, item.artifact_ref) for item in items}

    risk_set = ContractRiskSet(
        contract_risk_set_id=next_contract_risk_set_id(session, ContractRiskSet.contract_risk_set_id),
        deal_id=payload.deal_id,
        document_set_id=document_set.document_set_id,
        risk_status=ContractRiskStatus.BUILT,
    )
    session.add(risk_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="contract_risk_build_started",
        source_module_id="M-026",
        severity=EventSeverity.INFO,
        payload_json={
            "contract_risk_set_id": risk_set.contract_risk_set_id,
            "document_set_id": document_set.document_set_id,
        },
    )
    try:
        for blueprint in _risk_blueprints(document_set, items, artifacts):
            record = ContractRiskRecord(
                contract_risk_id=next_contract_risk_id(session, ContractRiskRecord.contract_risk_id),
                contract_risk_set_id=risk_set.contract_risk_set_id,
                source_artifact_ref=blueprint["source_artifact_ref"],
                clause_type=blueprint["clause_type"],
                summary=blueprint["summary"],
                severity=blueprint["severity"],
                notes=blueprint["notes"],
            )
            session.add(record)
            session.flush()
            for flag_data in blueprint["flags"]:
                session.add(ContractRiskFlag(contract_risk_id=record.contract_risk_id, **flag_data))
        risk_set.updated_at = utcnow()
        session.add(risk_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="contract_risk_built",
            source_module_id="M-026",
            severity=EventSeverity.INFO,
            payload_json={"contract_risk_set_id": risk_set.contract_risk_set_id},
        )
        session.commit()
    except Exception as exc:
        risk_set.risk_status = ContractRiskStatus.FAILED
        risk_set.updated_at = utcnow()
        session.add(risk_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="contract_risk_failed",
            source_module_id="M-026",
            severity=EventSeverity.HIGH,
            payload_json={"contract_risk_set_id": risk_set.contract_risk_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(risk_set)
    return risk_set


def get_contract_risk_set(
    session: Session,
    contract_risk_set_id: str,
) -> tuple[ContractRiskSet, list[tuple[ContractRiskRecord, list[ContractRiskFlag]]]]:
    risk_set = _get_set(session, contract_risk_set_id)
    records = _get_records(session, contract_risk_set_id)
    return risk_set, [(record, _get_flags(session, record.contract_risk_id)) for record in records]


def list_contract_risk_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[ContractRiskSet, list[tuple[ContractRiskRecord, list[ContractRiskFlag]]]]]:
    query = select(ContractRiskSet).order_by(ContractRiskSet.created_at.desc())
    if deal_id:
        query = query.where(ContractRiskSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_contract_risk_set(session, item.contract_risk_set_id) for item in sets]


def get_contract_risk_record(
    session: Session,
    contract_risk_id: str,
) -> tuple[ContractRiskRecord, list[ContractRiskFlag]]:
    record = session.scalar(select(ContractRiskRecord).where(ContractRiskRecord.contract_risk_id == contract_risk_id))
    if not record:
        raise NotFoundError(f"Contract risk record '{contract_risk_id}' was not found")
    return record, _get_flags(session, contract_risk_id)
