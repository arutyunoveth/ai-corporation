from datetime import datetime

from pydantic import Field

from src.shared.enums import ContractNegotiationStatus, RiskSeverity
from src.shared.types.common import APIModel


class BuildContractNegotiationRequest(APIModel):
    deal_id: str


class ContractNegotiationIssueResponse(APIModel):
    issue_code: str
    issue_text: str
    severity: RiskSeverity
    created_at: datetime


class ContractNegotiationCommentResponse(APIModel):
    clause_ref: str
    comment_text: str
    created_at: datetime


class ContractNegotiationRecordResponse(APIModel):
    contract_negotiation_id: str
    contract_negotiation_set_id: str
    summary_text: str
    negotiation_pack_manifest_json: dict
    created_at: datetime
    updated_at: datetime
    issues: list[ContractNegotiationIssueResponse] = Field(default_factory=list)
    comments: list[ContractNegotiationCommentResponse] = Field(default_factory=list)


class ContractNegotiationSetResponse(APIModel):
    contract_negotiation_set_id: str
    deal_id: str
    negotiation_status: ContractNegotiationStatus
    created_at: datetime
    updated_at: datetime
    records: list[ContractNegotiationRecordResponse] = Field(default_factory=list)
