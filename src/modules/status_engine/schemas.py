from datetime import datetime

from src.shared.enums import ChangedByType, DealStatus
from src.shared.types.common import APIModel


class ValidateTransitionRequest(APIModel):
    deal_id: str
    from_status: DealStatus | None = None
    to_status: DealStatus


class ValidateTransitionResponse(APIModel):
    allowed: bool
    reason: str | None = None


class ApplyTransitionRequest(APIModel):
    deal_id: str
    from_status: DealStatus | None = None
    to_status: DealStatus
    changed_by_type: ChangedByType
    changed_by_ref: str | None = None
    reason_code: str | None = None
    reason_text: str | None = None
    is_override: bool = False


class StatusHistoryEntry(APIModel):
    deal_id: str
    from_status: DealStatus | None
    to_status: DealStatus
    changed_by_type: ChangedByType
    changed_by_ref: str | None
    reason_code: str | None
    reason_text: str | None
    is_override: bool
    created_at: datetime

