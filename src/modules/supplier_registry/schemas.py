from datetime import datetime

from src.shared.enums import SupplierStatus
from src.shared.types.common import APIModel


class CreateSupplierRequest(APIModel):
    legal_name: str
    display_name: str
    inn: str
    country_code: str
    status: SupplierStatus = SupplierStatus.ACTIVE
    notes: str | None = None


class UpdateSupplierRequest(APIModel):
    legal_name: str | None = None
    display_name: str | None = None
    country_code: str | None = None
    status: SupplierStatus | None = None
    notes: str | None = None


class CreateSupplierContactRequest(APIModel):
    contact_name: str
    email: str | None = None
    phone: str | None = None
    is_primary: bool = False


class CreateSupplierTagRequest(APIModel):
    tag_code: str


class SupplierExternalRefResponse(APIModel):
    ref_type: str
    ref_value: str
    created_at: datetime


class SupplierContactResponse(APIModel):
    id: str
    supplier_id: str
    contact_name: str
    email: str | None
    phone: str | None
    is_primary: bool
    created_at: datetime


class SupplierTagResponse(APIModel):
    id: str
    supplier_id: str
    tag_code: str
    created_at: datetime


class SupplierProfileResponse(APIModel):
    supplier_id: str
    legal_name: str
    display_name: str
    inn: str
    country_code: str
    status: SupplierStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    duplicate_hint: bool = False
    external_refs: list[SupplierExternalRefResponse] = []
    contacts: list[SupplierContactResponse] = []
    tags: list[SupplierTagResponse] = []
