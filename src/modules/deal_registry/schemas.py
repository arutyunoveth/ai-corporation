from datetime import datetime

from pydantic import Field

from src.shared.enums import DealStatus, DirectionType, InitialSourceType, ProcurementChannel
from src.shared.types.common import APIModel


class CreateDealRequest(APIModel):
    title: str = Field(min_length=1)
    customer_name: str | None = None
    procurement_number: str | None = None
    procurement_channel: ProcurementChannel | None = None
    initial_source_type: InitialSourceType
    direction_type: DirectionType
    domain_type: str = Field(min_length=1)


class UpdateDealRequest(APIModel):
    title: str | None = Field(default=None, min_length=1)
    customer_name: str | None = None
    procurement_number: str | None = None
    procurement_channel: ProcurementChannel | None = None
    priority_bucket: str | None = None


class DealResponse(APIModel):
    deal_id: str
    title: str
    customer_name: str | None
    procurement_number: str | None
    procurement_channel: str | None
    initial_source_type: str
    direction_type: str
    domain_type: str
    current_status: DealStatus
    priority_bucket: str | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    is_deleted: bool


class CreateDealResponse(APIModel):
    deal_id: str
    current_status: DealStatus
    created_at: datetime

