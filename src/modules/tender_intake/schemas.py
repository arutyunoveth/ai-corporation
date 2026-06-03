from datetime import datetime

from pydantic import Field

from src.shared.enums import DirectionType, InitialSourceType, IntakeStatus, TenderSourceType
from src.shared.types.common import APIModel


class CreateTenderIntakeRequest(APIModel):
    source_type: TenderSourceType
    source_channel: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_customer_name: str = Field(min_length=1)
    source_procurement_number: str | None = None
    payload_json: dict
    initial_source_type: InitialSourceType
    direction_type: DirectionType
    domain_type: str = Field(min_length=1)


class TenderIntakeResponse(APIModel):
    intake_id: str
    deal_id: str
    source_type: TenderSourceType
    source_channel: str
    source_title: str
    source_customer_name: str
    source_procurement_number: str | None
    intake_status: IntakeStatus
    duplicate_hint: bool
    payload_json: dict
    payload_hash: str
    received_at: datetime
    normalized_at: datetime
    created_at: datetime
    updated_at: datetime


class CreateTenderIntakeResponse(APIModel):
    intake_id: str
    deal_id: str
    intake_status: IntakeStatus
    duplicate_hint: bool

