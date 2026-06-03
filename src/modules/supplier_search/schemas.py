from datetime import datetime

from src.shared.enums import SupplierShortlistStatus
from src.shared.types.common import APIModel


class BuildSupplierShortlistRequest(APIModel):
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str
    compliance_matrix_id: str | None = None
    document_requirement_set_id: str | None = None
    risk_flag_set_id: str | None = None


class SupplierShortlistRowResponse(APIModel):
    supplier_id: str
    rank_order: int
    inclusion_reason: str
    source_type: str
    created_at: datetime


class SupplierShortlistResponse(APIModel):
    supplier_shortlist_id: str
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str
    shortlist_status: SupplierShortlistStatus
    created_at: datetime
    updated_at: datetime
    rows: list[SupplierShortlistRowResponse]
