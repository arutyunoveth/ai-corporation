from datetime import datetime

from src.shared.enums import SupplierContractObligationStatus, SupplierContractStatus
from src.shared.types.common import APIModel


class BuildSupplierContractRequest(APIModel):
    deal_id: str
    supplier_id: str


class SupplierContractObligationResponse(APIModel):
    obligation_code: str
    obligation_text: str
    obligation_status: SupplierContractObligationStatus
    created_at: datetime


class SupplierContractCommentResponse(APIModel):
    clause_ref: str
    comment_text: str
    created_at: datetime


class SupplierContractRecordResponse(APIModel):
    supplier_contract_id: str
    summary_text: str
    contract_manifest_json: dict
    created_at: datetime
    updated_at: datetime
    obligations: list[SupplierContractObligationResponse]
    comments: list[SupplierContractCommentResponse]


class SupplierContractSetResponse(APIModel):
    supplier_contract_set_id: str
    deal_id: str
    supplier_id: str
    contract_status: SupplierContractStatus
    created_at: datetime
    updated_at: datetime
    records: list[SupplierContractRecordResponse]
