from datetime import datetime

from pydantic import Field

from src.shared.enums import CustomerStatus
from src.shared.types.common import APIModel


class CreateCustomerExternalRefRequest(APIModel):
    source_type: str
    source_ref: str


class CreateCustomerContourRequest(APIModel):
    contour_code: str
    contour_name: str
    notes: str | None = None


class CreateCustomerRequest(APIModel):
    legal_name: str
    inn: str | None = None
    kpp: str | None = None
    customer_status: CustomerStatus = CustomerStatus.PROSPECT
    deal_id: str | None = None
    external_refs: list[CreateCustomerExternalRefRequest] = Field(default_factory=list)
    contours: list[CreateCustomerContourRequest] = Field(default_factory=list)


class UpdateCustomerRequest(APIModel):
    legal_name: str | None = None
    inn: str | None = None
    kpp: str | None = None
    customer_status: CustomerStatus | None = None


class CustomerExternalRefResponse(APIModel):
    source_type: str
    source_ref: str
    created_at: datetime


class CustomerContourResponse(APIModel):
    contour_code: str
    contour_name: str
    notes: str | None
    created_at: datetime


class CustomerProfileResponse(APIModel):
    customer_id: str
    legal_name: str
    inn: str | None
    kpp: str | None
    customer_status: CustomerStatus
    created_at: datetime
    updated_at: datetime
    duplicate_hint: bool = False
    external_refs: list[CustomerExternalRefResponse] = Field(default_factory=list)
    contours: list[CustomerContourResponse] = Field(default_factory=list)
