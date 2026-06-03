from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.compliance_matrix.service import get_compliance_matrix
from src.modules.document_requirements.service import get_document_requirement_set
from src.modules.event_log.service import append_event_record
from src.modules.initial_tech_risks.models import InitialTechRiskFlag, InitialTechRiskFlagSet
from src.modules.initial_tech_risks.schemas import BuildInitialTechRisksRequest
from src.shared.analysis_package import load_intake_package
from src.shared.enums import ComplianceStatus, EventSeverity, TechRiskCategory, TechRiskSeverity
from src.shared.ids import next_risk_flag_set_id
from src.shared.validation import require_same_reference


def _severity_rank(severity: TechRiskSeverity) -> int:
    return {
        TechRiskSeverity.LOW: 1,
        TechRiskSeverity.MEDIUM: 2,
        TechRiskSeverity.HIGH: 3,
        TechRiskSeverity.CRITICAL: 4,
    }[severity]


def _build_flags(package, matrix_rows, requirement_rows) -> list[dict]:
    flags: list[dict] = []
    if not any(item.item_role == "TZ" for item in package.document_set_items):
        flags.append(
            {
                "row_code": "RISK-0001",
                "risk_code": "MISSING_TECHNICAL_SPEC",
                "risk_category": TechRiskCategory.INCOMPLETE_SPEC,
                "severity": TechRiskSeverity.HIGH,
                "summary": "Technical specification document is missing from the current tender package.",
                "source_ref": f"DOCUMENT_SET:{package.document_set.document_set_id}",
                "mitigation_hint": "Request or locate the technical specification before supplier-side work.",
                "requires_manual_review": True,
            }
        )

    for row in matrix_rows:
        if row.compliance_status == ComplianceStatus.UNKNOWN:
            flags.append(
                {
                    "row_code": f"RISK-{len(flags) + 1:04d}",
                    "risk_code": "UNKNOWN_COMPLIANCE_PATH",
                    "risk_category": TechRiskCategory.AMBIGUITY,
                    "severity": TechRiskSeverity.MEDIUM,
                    "summary": "A compliance row cannot yet be verified confidently.",
                    "source_ref": f"COMPLIANCE_MATRIX:{row.compliance_matrix_id}:{row.row_code}",
                    "mitigation_hint": "Review the source artifact and clarify the verification path.",
                    "requires_manual_review": True,
                }
            )
        elif row.compliance_status == ComplianceStatus.PARTIAL_MATCH:
            flags.append(
                {
                    "row_code": f"RISK-{len(flags) + 1:04d}",
                    "risk_code": "PARTIAL_REQUIREMENT_MATCH",
                    "risk_category": TechRiskCategory.INCOMPLETE_SPEC,
                    "severity": TechRiskSeverity.LOW,
                    "summary": "A requirement is only partially represented in the current intake package.",
                    "source_ref": f"COMPLIANCE_MATRIX:{row.compliance_matrix_id}:{row.row_code}",
                    "mitigation_hint": "Expand the intake package or confirm the missing detail manually.",
                    "requires_manual_review": row.requires_manual_review,
                }
            )

    for row in requirement_rows:
        if row.requirement_status == "UNKNOWN":
            flags.append(
                {
                    "row_code": f"RISK-{len(flags) + 1:04d}",
                    "risk_code": "UNKNOWN_DOCUMENT_REQUIREMENT",
                    "risk_category": TechRiskCategory.AMBIGUITY,
                    "severity": TechRiskSeverity.MEDIUM,
                    "summary": "A document requirement could not be confidently classified.",
                    "source_ref": f"DOCUMENT_REQUIREMENT:{row.document_requirement_set_id}:{row.row_code}",
                    "mitigation_hint": "Review the source document and classify the requirement before bid prep.",
                    "requires_manual_review": True,
                }
            )

    if not flags:
        flags.append(
            {
                "row_code": "RISK-0001",
                "risk_code": "BASELINE_REVIEW_RECOMMENDED",
                "risk_category": TechRiskCategory.OTHER,
                "severity": TechRiskSeverity.LOW,
                "summary": "No immediate hard-stop risks were found, but a baseline manual technical review is still recommended.",
                "source_ref": f"TENDER_SUMMARY:{package.tender_summary.tender_summary_id}",
                "mitigation_hint": "Proceed to the next analysis stage with routine manual verification.",
                "requires_manual_review": False,
            }
        )
    return flags


def build_initial_tech_risks(
    session: Session,
    payload: BuildInitialTechRisksRequest,
) -> tuple[InitialTechRiskFlagSet, list[InitialTechRiskFlag]]:
    package = load_intake_package(
        session,
        deal_id=payload.deal_id,
        intake_id=payload.intake_id,
        document_set_id=payload.document_set_id,
        tender_summary_id=payload.tender_summary_id,
    )
    matrix, matrix_rows = get_compliance_matrix(session, payload.compliance_matrix_id)
    requirement_set, requirement_rows = get_document_requirement_set(session, payload.document_requirement_set_id)
    require_same_reference(package.deal.deal_id, matrix.deal_id, "deal_id")
    require_same_reference(package.deal.deal_id, requirement_set.deal_id, "deal_id")
    append_event_record(
        session,
        deal_id=package.deal.deal_id,
        event_code="initial_tech_risk_build_started",
        source_module_id="M-015",
        severity=EventSeverity.INFO,
        payload_json={
            "compliance_matrix_id": matrix.compliance_matrix_id,
            "document_requirement_set_id": requirement_set.document_requirement_set_id,
        },
    )
    try:
        flags_data = _build_flags(package, matrix_rows, requirement_rows)
        overall_risk_severity = max(
            (flag["severity"] for flag in flags_data),
            key=_severity_rank,
        )
        summary_text = (
            f"Built {len(flags_data)} initial tech risk flags. "
            f"Overall severity: {overall_risk_severity}."
        )
        flag_set = InitialTechRiskFlagSet(
            risk_flag_set_id=next_risk_flag_set_id(session, InitialTechRiskFlagSet.risk_flag_set_id),
            deal_id=package.deal.deal_id,
            intake_id=package.intake.intake_id,
            document_set_id=package.document_set.document_set_id,
            tender_summary_id=package.tender_summary.tender_summary_id,
            compliance_matrix_id=matrix.compliance_matrix_id,
            document_requirement_set_id=requirement_set.document_requirement_set_id,
            risk_flag_count=len(flags_data),
            overall_risk_severity=overall_risk_severity,
            summary_text=summary_text,
        )
        session.add(flag_set)
        session.flush()
        flags: list[InitialTechRiskFlag] = []
        for flag_data in flags_data:
            flag = InitialTechRiskFlag(risk_flag_set_id=flag_set.risk_flag_set_id, **flag_data)
            session.add(flag)
            flags.append(flag)
        session.flush()
        append_event_record(
            session,
            deal_id=package.deal.deal_id,
            event_code="initial_tech_risk_built",
            source_module_id="M-015",
            severity=EventSeverity.INFO,
            payload_json={
                "risk_flag_set_id": flag_set.risk_flag_set_id,
                "risk_flag_count": flag_set.risk_flag_count,
                "overall_risk_severity": str(flag_set.overall_risk_severity),
            },
        )
        session.commit()
        session.refresh(flag_set)
        return flag_set, flags
    except Exception as exc:
        append_event_record(
            session,
            deal_id=package.deal.deal_id,
            event_code="initial_tech_risk_build_failed",
            source_module_id="M-015",
            severity=EventSeverity.HIGH,
            payload_json={"error": str(exc)},
        )
        session.commit()
        raise


def get_initial_tech_risk_set(
    session: Session,
    risk_flag_set_id: str,
) -> tuple[InitialTechRiskFlagSet, list[InitialTechRiskFlag]]:
    from src.shared.errors import NotFoundError

    flag_set = session.scalar(
        select(InitialTechRiskFlagSet).where(InitialTechRiskFlagSet.risk_flag_set_id == risk_flag_set_id)
    )
    if not flag_set:
        raise NotFoundError(f"Initial tech risk set '{risk_flag_set_id}' was not found")
    flags = list(
        session.scalars(
            select(InitialTechRiskFlag)
            .where(InitialTechRiskFlag.risk_flag_set_id == risk_flag_set_id)
            .order_by(InitialTechRiskFlag.created_at.asc(), InitialTechRiskFlag.id.asc())
        )
    )
    return flag_set, flags


def list_initial_tech_risk_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[InitialTechRiskFlagSet, list[InitialTechRiskFlag]]]:
    query = select(InitialTechRiskFlagSet).order_by(InitialTechRiskFlagSet.created_at.desc())
    if deal_id:
        query = query.where(InitialTechRiskFlagSet.deal_id == deal_id)
    flag_sets = list(session.scalars(query))
    return [get_initial_tech_risk_set(session, item.risk_flag_set_id) for item in flag_sets]

