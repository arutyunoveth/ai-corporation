from fastapi import APIRouter, Query, status

from src.modules.compliance_matrix.schemas import (
    BuildComplianceMatrixRequest,
    ComplianceMatrixResponse,
    ComplianceMatrixRowResponse,
)
from src.modules.compliance_matrix.service import build_compliance_matrix, get_compliance_matrix, list_compliance_matrices
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["compliance-matrix"])


def _to_response(result: tuple) -> ComplianceMatrixResponse:
    matrix, rows = result
    return ComplianceMatrixResponse(
        compliance_matrix_id=matrix.compliance_matrix_id,
        deal_id=matrix.deal_id,
        intake_id=matrix.intake_id,
        document_set_id=matrix.document_set_id,
        tender_summary_id=matrix.tender_summary_id,
        matrix_row_count=matrix.matrix_row_count,
        ambiguous_row_count=matrix.ambiguous_row_count,
        high_risk_row_count=matrix.high_risk_row_count,
        requires_manual_review=matrix.requires_manual_review,
        created_at=matrix.created_at,
        updated_at=matrix.updated_at,
        rows=[ComplianceMatrixRowResponse.model_validate(row) for row in rows],
    )


@router.post("/compliance-matrix/build", response_model=ComplianceMatrixResponse, status_code=status.HTTP_201_CREATED)
def build_compliance_matrix_route(payload: BuildComplianceMatrixRequest, session: DBSession) -> ComplianceMatrixResponse:
    return _to_response(build_compliance_matrix(session, payload))


@router.get("/compliance-matrix/{compliance_matrix_id}", response_model=ComplianceMatrixResponse)
def get_compliance_matrix_route(compliance_matrix_id: str, session: DBSession) -> ComplianceMatrixResponse:
    return _to_response(get_compliance_matrix(session, compliance_matrix_id))


@router.get("/compliance-matrix", response_model=list[ComplianceMatrixResponse])
def list_compliance_matrices_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[ComplianceMatrixResponse]:
    return [_to_response(item) for item in list_compliance_matrices(session, deal_id=deal_id)]

