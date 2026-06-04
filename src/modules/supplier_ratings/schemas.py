from datetime import datetime

from src.shared.enums import SupplierRatingBand, SupplierRatingStatus
from src.shared.types.common import APIModel


class BuildSupplierRatingUpdateRequest(APIModel):
    deal_id: str


class SupplierRatingFactorResponse(APIModel):
    factor_code: str
    factor_score: float
    summary: str
    created_at: datetime


class SupplierRatingUpdateRecordResponse(APIModel):
    supplier_rating_update_id: str
    prior_rating_value: float | None
    updated_rating_value: float
    rating_band: SupplierRatingBand
    rationale_text: str
    created_at: datetime
    updated_at: datetime
    factors: list[SupplierRatingFactorResponse]


class SupplierRatingUpdateSetResponse(APIModel):
    supplier_rating_update_set_id: str
    deal_id: str
    supplier_id: str
    supplier_contract_set_id: str
    postmortem_set_id: str
    rating_status: SupplierRatingStatus
    created_at: datetime
    updated_at: datetime
    records: list[SupplierRatingUpdateRecordResponse]
