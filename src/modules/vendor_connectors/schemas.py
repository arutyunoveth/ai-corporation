from datetime import datetime

from src.shared.enums import CapabilityStatus, ConnectorScopeType, VendorProfileStatus, VendorStatus
from src.shared.types.common import APIModel


class BuildVendorConnectorProfilesRequest(APIModel):
    scope_type: ConnectorScopeType
    scope_ref: str


class VendorConnectorCapabilityResponse(APIModel):
    capability_code: str
    capability_status: CapabilityStatus
    notes: str | None
    created_at: datetime


class VendorConnectorRecordResponse(APIModel):
    vendor_connector_id: str
    vendor_connector_set_id: str
    connector_registry_id: str
    vendor_code: str
    vendor_status: VendorStatus
    created_at: datetime
    updated_at: datetime
    capabilities: list[VendorConnectorCapabilityResponse]


class VendorConnectorSetResponse(APIModel):
    vendor_connector_set_id: str
    scope_type: ConnectorScopeType
    scope_ref: str
    profile_status: VendorProfileStatus
    created_at: datetime
    updated_at: datetime
    records: list[VendorConnectorRecordResponse]
