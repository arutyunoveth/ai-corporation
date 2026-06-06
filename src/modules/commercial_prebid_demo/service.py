import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from src.modules.commercial_prebid_demo.schemas import (
    CommercialPreBidDemoResponse,
    RunCommercialPreBidDemoRequest,
)
from src.modules.compliance_matrix.schemas import BuildComplianceMatrixRequest
from src.modules.compliance_matrix.service import build_compliance_matrix
from src.modules.controlled_llm_prebid.service import run_controlled_llm_prebid_analysis
from src.modules.contract_risks.schemas import BuildContractRiskRequest
from src.modules.contract_risks.service import build_contract_risks, get_contract_risk_set
from src.modules.document_ingestion.schemas import (
    CreateDocumentIngestionRunRequest,
    CreateDocumentSetRequest,
    DocumentSetItemInput,
)
from src.modules.document_ingestion.service import create_document_ingestion_run, create_document_set
from src.modules.document_requirements.schemas import ExtractDocumentRequirementsRequest
from src.modules.document_requirements.service import extract_document_requirements, get_document_requirement_set
from src.modules.document_store.schemas import CreateArtifactRequest
from src.modules.document_store.service import create_artifact
from src.modules.event_log.service import append_event_record
from src.modules.initial_tech_risks.schemas import BuildInitialTechRisksRequest
from src.modules.initial_tech_risks.service import build_initial_tech_risks, get_initial_tech_risk_set
from src.modules.requirement_extraction.service import build_requirement_extraction, get_requirement_extraction_set
from src.modules.tender_intake.schemas import CreateTenderIntakeRequest
from src.modules.tender_intake.service import create_tender_intake
from src.modules.tender_summary.schemas import BuildTenderSummaryRequest
from src.modules.tender_summary.service import build_tender_summary, get_tender_summary
from src.shared.enums import (
    ArtifactType,
    DirectionType,
    DocumentIngestionRunStatus,
    DocumentSetItemRole,
    DocumentSetType,
    EventSeverity,
    InitialSourceType,
    TenderSourceType,
)
from src.shared.errors import NotFoundError


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
PILOT_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "pilot_tenders"


def available_fixture_dirs() -> list[Path]:
    return [FIXTURES_DIR, PILOT_FIXTURES_DIR]


def _load_fixture(fixture_name: str) -> dict:
    for directory in available_fixture_dirs():
        fixture_path = directory / f"{fixture_name}.json"
        if fixture_path.exists():
            return json.loads(fixture_path.read_text(encoding="utf-8"))
    raise NotFoundError(f"Commercial pre-bid demo fixture '{fixture_name}' was not found")


def _build_artifact_uri(deal_id: str, file_name: str) -> str:
    return f"demo://commercial-prebid/{deal_id}/{file_name}"


def _severity_rank(severity: str) -> int:
    return {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.get(str(severity), 0)


def _derive_recommendation(requirement_rows, tech_risk_flags, contract_risk_records) -> tuple[str, list[str]]:
    has_manual_review = any(row.requires_manual_review for row in requirement_rows)
    max_tech = max((_severity_rank(flag.severity) for flag in tech_risk_flags), default=0)
    max_contract = max((_severity_rank(record.severity) for record, _flags in contract_risk_records), default=0)
    has_missing_contract = any(
        any(flag.flag_code == "MISSING_DRAFT_CONTRACT" for flag in flags) for _record, flags in contract_risk_records
    )

    if has_missing_contract or max_tech >= 4:
        recommendation = "NEEDS_REVIEW"
    elif has_manual_review or max_contract >= 3 or max_tech >= 2:
        recommendation = "GO_WITH_CONDITIONS"
    else:
        recommendation = "GO"

    next_actions = [
        "Validate participant qualification package against the required document list.",
        "Confirm the acceptance and payment clauses in the draft contract before bid drafting.",
    ]
    if recommendation == "NEEDS_REVIEW":
        next_actions.insert(0, "Stop before bid drafting and complete a manual legal/technical review.")
    else:
        next_actions.insert(0, "Proceed to internal commercial review with explicit human approval.")
    return recommendation, next_actions


def _build_report(
    fixture: dict,
    *,
    analysis_mode: str,
    deal_id: str,
    intake,
    document_set,
    summary,
    requirement_records,
    document_requirement_rows,
    tech_risk_flags,
    contract_risk_records,
    llm_analysis=None,
) -> tuple[str, dict]:
    recommendation, next_actions = _derive_recommendation(
        document_requirement_rows,
        tech_risk_flags,
        contract_risk_records,
    )
    report_json = {
        "fixture_name": fixture["fixture_name"],
        "analysis_mode": analysis_mode,
        "deal_id": deal_id,
        "intake_id": intake.intake_id,
        "document_set_id": document_set.document_set_id,
        "summary": {
            "title": summary.structured_summary_json.get("title"),
            "customer_name": summary.structured_summary_json.get("customer_name"),
            "procurement_number": summary.structured_summary_json.get("procurement_number"),
            "why_relevant": fixture["why_relevant"],
        },
        "technical_requirements": [
            record.requirement_text for record, _links in requirement_records
        ] + [row.requirement_title for row in document_requirement_rows],
        "participant_requirements": fixture["participant_requirements"],
        "required_documents": fixture["required_documents"],
        "contract_risks": [
            {
                "summary": record.summary,
                "severity": str(record.severity),
                "flags": [flag.summary for flag in flags],
            }
            for record, flags in contract_risk_records
        ],
        "supplier_questions": fixture["sample_supplier_questions"],
        "sample_supplier_quotes": fixture["sample_supplier_quotes"],
        "preliminary_recommendation": recommendation,
        "next_actions": next_actions,
    }
    if llm_analysis is not None:
        report_json["llm_analysis"] = {
            "overall_review_status": llm_analysis.overall_review_status,
            "sections": llm_analysis.sections,
            "trace_ids": llm_analysis.trace_ids,
        }

    technical_lines = "\n".join(
        f"- {item}" for item in report_json["technical_requirements"][:6]
    )
    participant_lines = "\n".join(f"- {item}" for item in report_json["participant_requirements"])
    documents_lines = "\n".join(f"- {item}" for item in report_json["required_documents"])
    contract_lines = "\n".join(
        f"- [{item['severity']}] {item['summary']}" for item in report_json["contract_risks"]
    )
    questions_lines = "\n".join(f"- {item}" for item in report_json["supplier_questions"])
    actions_lines = "\n".join(f"- {item}" for item in report_json["next_actions"])

    markdown = (
        "# Commercial Pre-Bid Demo Report\n\n"
        f"## Tender Summary\n"
        f"- Title: {report_json['summary']['title']}\n"
        f"- Customer: {report_json['summary']['customer_name']}\n"
        f"- Procurement number: {report_json['summary']['procurement_number']}\n"
        f"- Deal: {deal_id}\n"
        f"- Why it is relevant: {report_json['summary']['why_relevant']}\n\n"
        "## Technical Requirements\n"
        f"{technical_lines}\n\n"
        "## Participant Requirements\n"
        f"{participant_lines}\n\n"
        "## Required Documents\n"
        f"{documents_lines}\n\n"
        "## Contract Risks\n"
        f"{contract_lines}\n\n"
        "## Supplier Questions\n"
        f"{questions_lines}\n\n"
        "## Decision Recommendation\n"
        f"- Preliminary recommendation: {report_json['preliminary_recommendation']}\n"
        "- Human review required: yes\n"
        "- Analysis mode: deterministic\n\n"
        "## Next Actions\n"
        f"{actions_lines}\n"
    )
    if llm_analysis is not None:
        llm_lines = []
        for section_name, section in llm_analysis.sections.items():
            llm_lines.append(
                f"- {section_name}: validation={section['validation_status']}, review={section['review_status']}, trace={section['trace_id']}"
            )
        markdown += (
            "\n## Controlled LLM Review\n"
            f"- Overall review status: {llm_analysis.overall_review_status}\n"
            f"- Analysis mode: {llm_analysis.analysis_mode}\n"
            + "\n".join(llm_lines)
            + "\n"
        )
    return markdown, report_json


def run_commercial_prebid_demo(
    session: Session,
    payload: RunCommercialPreBidDemoRequest,
) -> CommercialPreBidDemoResponse:
    fixture = _load_fixture(payload.fixture_name)
    intake = None
    try:
        intake, _source_payload = create_tender_intake(
            session,
            CreateTenderIntakeRequest(
                source_type=TenderSourceType.MANUAL,
                source_channel="commercial_demo_fixture",
                source_title=fixture["tender"]["source_title"],
                source_customer_name=fixture["tender"]["source_customer_name"],
                source_procurement_number=fixture["tender"]["source_procurement_number"],
                payload_json={
                    "portal_url": fixture["tender"]["portal_url"],
                    "notice_date": fixture["tender"]["notice_date"],
                    "notice_text": fixture["notice_text"],
                    "technical_specification_text": fixture["technical_specification_text"],
                    "contract_draft_text": fixture["contract_draft_text"],
                    "fixture_name": fixture["fixture_name"],
                },
                initial_source_type=InitialSourceType.MANUAL_ENTRY,
                direction_type=DirectionType[fixture["tender"]["direction_type"]],
                domain_type=fixture["tender"]["domain_type"],
            ),
        )
        append_event_record(
            session,
            deal_id=intake.deal_id,
            event_code="commercial_prebid_demo_started",
            source_module_id="C2",
            severity=EventSeverity.INFO,
            payload_json={"fixture_name": fixture["fixture_name"], "intake_id": intake.intake_id},
        )
        session.commit()

        notice_artifact = create_artifact(
            session,
            CreateArtifactRequest(
                deal_id=intake.deal_id,
                artifact_type=ArtifactType.TENDER_DOC,
                file_name="commercial-demo-notice.txt",
                mime_type="text/plain",
                storage_uri=_build_artifact_uri(intake.deal_id, "notice.txt"),
                checksum_sha256="commercial-demo-notice",
            ),
        )
        spec_artifact = create_artifact(
            session,
            CreateArtifactRequest(
                deal_id=intake.deal_id,
                artifact_type=ArtifactType.TENDER_DOC,
                file_name="commercial-demo-technical-specification.txt",
                mime_type="text/plain",
                storage_uri=_build_artifact_uri(intake.deal_id, "technical-specification.txt"),
                checksum_sha256="commercial-demo-technical-specification",
            ),
        )
        contract_artifact = create_artifact(
            session,
            CreateArtifactRequest(
                deal_id=intake.deal_id,
                artifact_type=ArtifactType.TENDER_DOC,
                file_name="commercial-demo-draft-contract.txt",
                mime_type="text/plain",
                storage_uri=_build_artifact_uri(intake.deal_id, "draft-contract.txt"),
                checksum_sha256="commercial-demo-draft-contract",
            ),
        )
        document_set = create_document_set(
            session,
            CreateDocumentSetRequest(
                deal_id=intake.deal_id,
                intake_id=intake.intake_id,
                set_type=DocumentSetType.TENDER_INITIAL,
                items=[
                    DocumentSetItemInput(
                        artifact_ref=notice_artifact.artifact_ref,
                        item_role=DocumentSetItemRole.NOTICE,
                        source_file_name=notice_artifact.file_name,
                        sort_order=1,
                    ),
                    DocumentSetItemInput(
                        artifact_ref=spec_artifact.artifact_ref,
                        item_role=DocumentSetItemRole.TZ,
                        source_file_name=spec_artifact.file_name,
                        sort_order=2,
                    ),
                    DocumentSetItemInput(
                        artifact_ref=contract_artifact.artifact_ref,
                        item_role=DocumentSetItemRole.DRAFT_CONTRACT,
                        source_file_name=contract_artifact.file_name,
                        sort_order=3,
                    ),
                ],
            ),
        )
        create_document_ingestion_run(
            session,
            document_set.document_set_id,
            CreateDocumentIngestionRunRequest(
                run_status=DocumentIngestionRunStatus.COMPLETED,
                notes="Commercial demo fixture ingestion completed.",
            ),
        )
        requirement_extraction = build_requirement_extraction(session, document_set.document_set_id)
        summary = build_tender_summary(
            session,
            BuildTenderSummaryRequest(
                deal_id=intake.deal_id,
                intake_id=intake.intake_id,
                document_set_id=document_set.document_set_id,
            ),
        )
        compliance_matrix, _rows = build_compliance_matrix(
            session,
            BuildComplianceMatrixRequest(
                deal_id=intake.deal_id,
                intake_id=intake.intake_id,
                document_set_id=document_set.document_set_id,
                tender_summary_id=summary.tender_summary_id,
            ),
        )
        document_requirements, _document_requirement_rows = extract_document_requirements(
            session,
            ExtractDocumentRequirementsRequest(
                deal_id=intake.deal_id,
                intake_id=intake.intake_id,
                document_set_id=document_set.document_set_id,
                tender_summary_id=summary.tender_summary_id,
            ),
        )
        risk_flag_set, _risk_flags = build_initial_tech_risks(
            session,
            BuildInitialTechRisksRequest(
                deal_id=intake.deal_id,
                intake_id=intake.intake_id,
                document_set_id=document_set.document_set_id,
                tender_summary_id=summary.tender_summary_id,
                compliance_matrix_id=compliance_matrix.compliance_matrix_id,
                document_requirement_set_id=document_requirements.document_requirement_set_id,
            ),
        )
        contract_risk_set = build_contract_risks(
            session,
            BuildContractRiskRequest(
                deal_id=intake.deal_id,
                document_set_id=document_set.document_set_id,
            ),
        )

        summary, _summary_links = get_tender_summary(session, summary.tender_summary_id)
        _req_set, requirement_records = get_requirement_extraction_set(
            session, requirement_extraction.requirement_extraction_set_id
        )
        _doc_req_set, document_requirement_rows = get_document_requirement_set(
            session, document_requirements.document_requirement_set_id
        )
        _risk_set, tech_risk_flags = get_initial_tech_risk_set(session, risk_flag_set.risk_flag_set_id)
        _contract_set, contract_risk_records = get_contract_risk_set(session, contract_risk_set.contract_risk_set_id)
        llm_analysis = None
        analysis_mode = "deterministic"
        if payload.provider != "deterministic":
            llm_context = {
                "deal_id": intake.deal_id,
                "title": summary.structured_summary_json.get("title"),
                "customer_name": summary.structured_summary_json.get("customer_name"),
                "participant_requirements": fixture["participant_requirements"],
                "required_documents": fixture["required_documents"],
                "contract_risks": [record.summary for record, _flags in contract_risk_records],
            }
            llm_analysis = run_controlled_llm_prebid_analysis(
                session,
                provider_mode=payload.provider,
                context=llm_context,
                simulate_invalid_output=payload.simulate_invalid_output,
            )
            analysis_mode = llm_analysis.analysis_mode

        report_markdown, report_json = _build_report(
            fixture,
            analysis_mode=analysis_mode,
            deal_id=intake.deal_id,
            intake=intake,
            document_set=document_set,
            summary=summary,
            requirement_records=requirement_records,
            document_requirement_rows=document_requirement_rows,
            tech_risk_flags=tech_risk_flags,
            contract_risk_records=contract_risk_records,
            llm_analysis=llm_analysis,
        )
        append_event_record(
            session,
            deal_id=intake.deal_id,
            event_code="commercial_prebid_demo_report_built",
            source_module_id="C2",
            severity=EventSeverity.INFO,
            payload_json={
                "fixture_name": fixture["fixture_name"],
                "document_set_id": document_set.document_set_id,
                "contract_risk_set_id": contract_risk_set.contract_risk_set_id,
            },
        )
        session.commit()
        return CommercialPreBidDemoResponse(
            fixture_name=fixture["fixture_name"],
            analysis_mode=analysis_mode,
            generated_at=datetime.now(UTC),
            deal_id=intake.deal_id,
            intake_id=intake.intake_id,
            document_set_id=document_set.document_set_id,
            tender_summary_id=summary.tender_summary_id,
            requirement_extraction_set_id=requirement_extraction.requirement_extraction_set_id,
            document_requirement_set_id=document_requirements.document_requirement_set_id,
            risk_flag_set_id=risk_flag_set.risk_flag_set_id,
            contract_risk_set_id=contract_risk_set.contract_risk_set_id,
            report_markdown=report_markdown,
            report_json=report_json,
        )
    except Exception as exc:
        if intake is not None:
            append_event_record(
                session,
                deal_id=intake.deal_id,
                event_code="commercial_prebid_demo_failed",
                source_module_id="C2",
                severity=EventSeverity.HIGH,
                payload_json={"fixture_name": payload.fixture_name, "error": str(exc)},
            )
            session.commit()
        raise
