from datetime import datetime

from src.shared.enums import SupplierVerificationResult, SupplierVerificationStatus, VerificationFlagSeverity
from src.shared.types.common import APIModel


class BuildSupplierVerificationRequest(APIModel):
    deal_id: str
    supplier_shortlist_id: str


class SupplierVerificationFlagResponse(APIModel):
    flag_code: str
    severity: VerificationFlagSeverity
    summary: str
    source_ref: str | None
    created_at: datetime


class SupplierVerificationRecordResponse(APIModel):
    supplier_verification_id: str
    supplier_verification_set_id: str
    supplier_id: str
    verification_result: SupplierVerificationResult
    confidence_score: float
    notes: str | None
    created_at: datetime
    updated_at: datetime
    flags: list[SupplierVerificationFlagResponse]


class SupplierVerificationSetResponse(APIModel):
    supplier_verification_set_id: str
    deal_id: str
    supplier_shortlist_id: str
    verification_status: SupplierVerificationStatus
    created_at: datetime
    updated_at: datetime
    records: list[SupplierVerificationRecordResponse]
