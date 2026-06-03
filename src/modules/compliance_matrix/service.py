from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.compliance_matrix.models import ComplianceMatrix, ComplianceMatrixRow
from src.modules.compliance_matrix.schemas import BuildComplianceMatrixRequest
from src.modules.event_log.service import append_event_record
from src.shared.analysis_package import load_intake_package
from src.shared.enums import ComplianceStatus, EventSeverity
from src.shared.ids import next_compliance_matrix_id


def _build_rows(package) -> list[dict]:
    rows: list[dict] = []
    structured_summary = package.tender_summary.structured_summary_json
    rows.append(
        {
            "row_code": "CMR-0001",
            "sequence_no": 1,
            "requirement_text": "Tender summary should contain a readable high-level scope.",
            "requirement_category": "SUMMARY_SCOPE",
            "compliance_status": ComplianceStatus.MATCH if structured_summary.get("high_level_scope") else ComplianceStatus.PARTIAL_MATCH,
            "source_artifact_ref": None,
            "source_pointer": f"TENDER_SUMMARY:{package.tender_summary.tender_summary_id}",
            "notes": None if structured_summary.get("high_level_scope") else "Summary scope is incomplete.",
            "is_mandatory": True,
            "requires_manual_review": not bool(structured_summary.get("high_level_scope")),
        }
    )
    rows.append(
        {
            "row_code": "CMR-0002",
            "sequence_no": 2,
            "requirement_text": "Procurement metadata should include a procurement number for downstream traceability.",
            "requirement_category": "PROCUREMENT_METADATA",
            "compliance_status": ComplianceStatus.MATCH if package.deal.procurement_number else ComplianceStatus.UNKNOWN,
            "source_artifact_ref": None,
            "source_pointer": f"INTAKE:{package.intake.intake_id}",
            "notes": None if package.deal.procurement_number else "Procurement number is missing from the intake package.",
            "is_mandatory": True,
            "requires_manual_review": not bool(package.deal.procurement_number),
        }
    )
    for offset, item in enumerate(package.document_set_items, start=3):
        if item.item_role in {"NOTICE", "TZ"}:
            status = ComplianceStatus.MATCH
            review = False
            notes = "Primary source artifact is available."
        elif item.item_role == "DRAFT_CONTRACT":
            status = ComplianceStatus.PARTIAL_MATCH
            review = False
            notes = "Contract artifact exists but may still require downstream legal parsing."
        else:
            status = ComplianceStatus.UNKNOWN
            review = True
            notes = "Artifact role is generic and needs manual interpretation."
        rows.append(
            {
                "row_code": f"CMR-{offset:04d}",
                "sequence_no": offset,
                "requirement_text": f"Artifact role {item.item_role} should be reviewable as part of the tender package.",
                "requirement_category": item.item_role,
                "compliance_status": status,
                "source_artifact_ref": item.artifact_ref,
                "source_pointer": f"DOCUMENT_SET:{package.document_set.document_set_id}:{item.row_code if hasattr(item, 'row_code') else item.source_file_name}",
                "notes": notes,
                "is_mandatory": item.item_role in {"NOTICE", "TZ"},
                "requires_manual_review": review,
            }
        )
    return rows


def build_compliance_matrix(session: Session, payload: BuildComplianceMatrixRequest) -> tuple[ComplianceMatrix, list[ComplianceMatrixRow]]:
    package = load_intake_package(
        session,
        deal_id=payload.deal_id,
        intake_id=payload.intake_id,
        document_set_id=payload.document_set_id,
        tender_summary_id=payload.tender_summary_id,
    )
    append_event_record(
        session,
        deal_id=package.deal.deal_id,
        event_code="compliance_matrix_build_started",
        source_module_id="M-013",
        severity=EventSeverity.INFO,
        payload_json={"document_set_id": package.document_set.document_set_id},
    )
    try:
        rows_data = _build_rows(package)
        ambiguous_row_count = sum(1 for row in rows_data if row["requires_manual_review"])
        high_risk_row_count = sum(1 for row in rows_data if row["compliance_status"] in {ComplianceStatus.UNKNOWN, ComplianceStatus.CONFLICT})
        matrix = ComplianceMatrix(
            compliance_matrix_id=next_compliance_matrix_id(session, ComplianceMatrix.compliance_matrix_id),
            deal_id=package.deal.deal_id,
            intake_id=package.intake.intake_id,
            document_set_id=package.document_set.document_set_id,
            tender_summary_id=package.tender_summary.tender_summary_id,
            matrix_row_count=len(rows_data),
            ambiguous_row_count=ambiguous_row_count,
            high_risk_row_count=high_risk_row_count,
            requires_manual_review=ambiguous_row_count > 0,
        )
        session.add(matrix)
        session.flush()
        rows: list[ComplianceMatrixRow] = []
        for row_data in rows_data:
            row = ComplianceMatrixRow(compliance_matrix_id=matrix.compliance_matrix_id, **row_data)
            session.add(row)
            rows.append(row)
        session.flush()
        append_event_record(
            session,
            deal_id=package.deal.deal_id,
            event_code="compliance_matrix_built",
            source_module_id="M-013",
            severity=EventSeverity.INFO,
            payload_json={
                "compliance_matrix_id": matrix.compliance_matrix_id,
                "matrix_row_count": matrix.matrix_row_count,
            },
        )
        session.commit()
        session.refresh(matrix)
        return matrix, rows
    except Exception as exc:
        append_event_record(
            session,
            deal_id=package.deal.deal_id,
            event_code="compliance_matrix_failed",
            source_module_id="M-013",
            severity=EventSeverity.HIGH,
            payload_json={"error": str(exc)},
        )
        session.commit()
        raise


def get_compliance_matrix(session: Session, compliance_matrix_id: str) -> tuple[ComplianceMatrix, list[ComplianceMatrixRow]]:
    from src.shared.errors import NotFoundError

    matrix = session.scalar(
        select(ComplianceMatrix).where(ComplianceMatrix.compliance_matrix_id == compliance_matrix_id)
    )
    if not matrix:
        raise NotFoundError(f"Compliance matrix '{compliance_matrix_id}' was not found")
    rows = list(
        session.scalars(
            select(ComplianceMatrixRow)
            .where(ComplianceMatrixRow.compliance_matrix_id == compliance_matrix_id)
            .order_by(ComplianceMatrixRow.sequence_no.asc(), ComplianceMatrixRow.id.asc())
        )
    )
    return matrix, rows


def list_compliance_matrices(session: Session, *, deal_id: str | None = None) -> list[tuple[ComplianceMatrix, list[ComplianceMatrixRow]]]:
    query = select(ComplianceMatrix).order_by(ComplianceMatrix.created_at.desc())
    if deal_id:
        query = query.where(ComplianceMatrix.deal_id == deal_id)
    matrices = list(session.scalars(query))
    return [get_compliance_matrix(session, matrix.compliance_matrix_id) for matrix in matrices]

