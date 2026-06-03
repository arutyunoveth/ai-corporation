from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.modules.compliance_matrix.service import get_compliance_matrix
from src.modules.deal_registry.service import get_deal
from src.modules.document_ingestion.service import get_document_set
from src.modules.document_requirements.service import get_document_requirement_set
from src.modules.initial_tech_risks.service import get_initial_tech_risk_set
from src.modules.priority_scoring.service import get_priority_score
from src.modules.tender_intake.service import get_tender_intake
from src.modules.tender_screening.service import get_screening
from src.modules.tender_summary.service import get_tender_summary
from src.shared.validation import require_same_reference


@dataclass(slots=True)
class AnalysisPackage:
    deal: object
    deal_id: str
    intake: object
    intake_payload: object
    document_set: object
    document_set_items: list
    tender_summary: object
    compliance_matrix: object | None = None
    compliance_rows: list | None = None
    document_requirement_set: object | None = None
    document_requirement_rows: list | None = None
    risk_flag_set: object | None = None
    risk_flags: list | None = None
    screening: object | None = None
    priority_score: object | None = None


def load_analysis_package(
    session: Session,
    *,
    deal_id: str,
    intake_id: str,
    document_set_id: str,
    tender_summary_id: str,
    compliance_matrix_id: str | None = None,
    document_requirement_set_id: str | None = None,
    risk_flag_set_id: str | None = None,
    screening_id: str | None = None,
    priority_score_id: str | None = None,
) -> AnalysisPackage:
    intake, intake_payload = get_tender_intake(session, intake_id)
    deal = get_deal(session, deal_id)
    document_set, document_set_items, _ = get_document_set(session, document_set_id)
    tender_summary, _ = get_tender_summary(session, tender_summary_id)

    require_same_reference(deal_id, intake.deal_id, "deal_id")
    require_same_reference(deal_id, document_set.deal_id, "deal_id")
    require_same_reference(deal_id, tender_summary.deal_id, "deal_id")
    require_same_reference(intake_id, document_set.intake_id, "intake_id")
    require_same_reference(intake_id, tender_summary.intake_id, "intake_id")
    require_same_reference(document_set_id, tender_summary.document_set_id, "document_set_id")

    package = AnalysisPackage(
        deal_id=deal_id,
        deal=deal,
        intake=intake,
        intake_payload=intake_payload,
        document_set=document_set,
        document_set_items=document_set_items,
        tender_summary=tender_summary,
    )

    if compliance_matrix_id:
        compliance_matrix, compliance_rows = get_compliance_matrix(session, compliance_matrix_id)
        require_same_reference(deal_id, compliance_matrix.deal_id, "deal_id")
        require_same_reference(intake_id, compliance_matrix.intake_id, "intake_id")
        require_same_reference(document_set_id, compliance_matrix.document_set_id, "document_set_id")
        require_same_reference(tender_summary_id, compliance_matrix.tender_summary_id, "tender_summary_id")
        package.compliance_matrix = compliance_matrix
        package.compliance_rows = compliance_rows

    if document_requirement_set_id:
        requirement_set, requirement_rows = get_document_requirement_set(session, document_requirement_set_id)
        require_same_reference(deal_id, requirement_set.deal_id, "deal_id")
        require_same_reference(intake_id, requirement_set.intake_id, "intake_id")
        require_same_reference(document_set_id, requirement_set.document_set_id, "document_set_id")
        require_same_reference(tender_summary_id, requirement_set.tender_summary_id, "tender_summary_id")
        package.document_requirement_set = requirement_set
        package.document_requirement_rows = requirement_rows

    if risk_flag_set_id:
        risk_flag_set, risk_flags = get_initial_tech_risk_set(session, risk_flag_set_id)
        require_same_reference(deal_id, risk_flag_set.deal_id, "deal_id")
        require_same_reference(intake_id, risk_flag_set.intake_id, "intake_id")
        require_same_reference(document_set_id, risk_flag_set.document_set_id, "document_set_id")
        require_same_reference(tender_summary_id, risk_flag_set.tender_summary_id, "tender_summary_id")
        package.risk_flag_set = risk_flag_set
        package.risk_flags = risk_flags

    if screening_id:
        screening = get_screening(session, screening_id)
        require_same_reference(deal_id, screening.deal_id, "deal_id")
        require_same_reference(intake_id, screening.intake_id, "intake_id")
        require_same_reference(document_set_id, screening.document_set_id, "document_set_id")
        require_same_reference(tender_summary_id, screening.tender_summary_id, "tender_summary_id")
        package.screening = screening

    if priority_score_id:
        priority_score = get_priority_score(session, priority_score_id)
        require_same_reference(deal_id, priority_score.deal_id, "deal_id")
        require_same_reference(intake_id, priority_score.intake_id, "intake_id")
        require_same_reference(document_set_id, priority_score.document_set_id, "document_set_id")
        require_same_reference(tender_summary_id, priority_score.tender_summary_id, "tender_summary_id")
        package.priority_score = priority_score

    return package
