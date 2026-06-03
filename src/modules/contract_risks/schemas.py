from datetime import datetime

from src.shared.enums import ContractClauseType, ContractRiskStatus, RiskSeverity
from src.shared.types.common import APIModel


class BuildContractRiskRequest(APIModel):
    deal_id: str
    document_set_id: str


class ContractRiskFlagResponse(APIModel):
    flag_code: str
    severity: RiskSeverity
    summary: str
    source_ref: str | None
    created_at: datetime


class ContractRiskRecordResponse(APIModel):
    contract_risk_id: str
    contract_risk_set_id: str
    source_artifact_ref: str | None
    clause_type: ContractClauseType
    summary: str
    severity: RiskSeverity
    notes: str | None
    created_at: datetime
    updated_at: datetime
    flags: list[ContractRiskFlagResponse]


class ContractRiskSetResponse(APIModel):
    contract_risk_set_id: str
    deal_id: str
    document_set_id: str
    risk_status: ContractRiskStatus
    created_at: datetime
    updated_at: datetime
    records: list[ContractRiskRecordResponse]
