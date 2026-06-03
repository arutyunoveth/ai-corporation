from fastapi import APIRouter, Query, status

from src.modules.initial_tech_risks.schemas import (
    BuildInitialTechRisksRequest,
    InitialTechRiskFlagResponse,
    InitialTechRiskFlagSetResponse,
)
from src.modules.initial_tech_risks.service import (
    build_initial_tech_risks,
    get_initial_tech_risk_set,
    list_initial_tech_risk_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["initial-tech-risks"])


def _to_response(result: tuple) -> InitialTechRiskFlagSetResponse:
    flag_set, flags = result
    return InitialTechRiskFlagSetResponse(
        risk_flag_set_id=flag_set.risk_flag_set_id,
        deal_id=flag_set.deal_id,
        intake_id=flag_set.intake_id,
        document_set_id=flag_set.document_set_id,
        tender_summary_id=flag_set.tender_summary_id,
        compliance_matrix_id=flag_set.compliance_matrix_id,
        document_requirement_set_id=flag_set.document_requirement_set_id,
        risk_flag_count=flag_set.risk_flag_count,
        overall_risk_severity=flag_set.overall_risk_severity,
        summary_text=flag_set.summary_text,
        created_at=flag_set.created_at,
        updated_at=flag_set.updated_at,
        flags=[InitialTechRiskFlagResponse.model_validate(flag) for flag in flags],
    )


@router.post(
    "/initial-tech-risks/build",
    response_model=InitialTechRiskFlagSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def build_initial_tech_risks_route(
    payload: BuildInitialTechRisksRequest,
    session: DBSession,
) -> InitialTechRiskFlagSetResponse:
    return _to_response(build_initial_tech_risks(session, payload))


@router.get("/initial-tech-risks/{risk_flag_set_id}", response_model=InitialTechRiskFlagSetResponse)
def get_initial_tech_risk_set_route(
    risk_flag_set_id: str,
    session: DBSession,
) -> InitialTechRiskFlagSetResponse:
    return _to_response(get_initial_tech_risk_set(session, risk_flag_set_id))


@router.get("/initial-tech-risks", response_model=list[InitialTechRiskFlagSetResponse])
def list_initial_tech_risk_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[InitialTechRiskFlagSetResponse]:
    return [_to_response(item) for item in list_initial_tech_risk_sets(session, deal_id=deal_id)]
