from fastapi import APIRouter, Query, status

from src.modules.vendor_connectors.schemas import (
    BuildVendorConnectorProfilesRequest,
    VendorConnectorCapabilityResponse,
    VendorConnectorRecordResponse,
    VendorConnectorSetResponse,
)
from src.modules.vendor_connectors.service import (
    build_vendor_connector_profiles,
    get_vendor_connector_record,
    get_vendor_connector_set,
    list_vendor_connector_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import ConnectorScopeType

router = APIRouter(tags=["vendor-connectors"])


def _to_capability_response(item) -> VendorConnectorCapabilityResponse:
    return VendorConnectorCapabilityResponse.model_validate(item)


def _to_record_response(result: tuple) -> VendorConnectorRecordResponse:
    record, capabilities = result
    return VendorConnectorRecordResponse(
        vendor_connector_id=record.vendor_connector_id,
        vendor_connector_set_id=record.vendor_connector_set_id,
        connector_registry_id=record.connector_registry_id,
        vendor_code=record.vendor_code,
        vendor_status=record.vendor_status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        capabilities=[_to_capability_response(item) for item in capabilities],
    )


def _to_set_response(result: tuple) -> VendorConnectorSetResponse:
    vendor_set, records = result
    return VendorConnectorSetResponse(
        vendor_connector_set_id=vendor_set.vendor_connector_set_id,
        scope_type=vendor_set.scope_type,
        scope_ref=vendor_set.scope_ref,
        profile_status=vendor_set.profile_status,
        created_at=vendor_set.created_at,
        updated_at=vendor_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/vendor-connectors/build", response_model=VendorConnectorSetResponse, status_code=status.HTTP_201_CREATED)
def build_vendor_connector_profiles_route(
    payload: BuildVendorConnectorProfilesRequest,
    session: DBSession,
) -> VendorConnectorSetResponse:
    vendor_set = build_vendor_connector_profiles(session, payload)
    return _to_set_response(get_vendor_connector_set(session, vendor_set.vendor_connector_set_id))


@router.get("/vendor-connectors/{vendor_connector_set_id}", response_model=VendorConnectorSetResponse)
def get_vendor_connector_set_route(vendor_connector_set_id: str, session: DBSession) -> VendorConnectorSetResponse:
    return _to_set_response(get_vendor_connector_set(session, vendor_connector_set_id))


@router.get("/vendor-connectors", response_model=list[VendorConnectorSetResponse])
def list_vendor_connector_sets_route(
    session: DBSession,
    scope_type: ConnectorScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[VendorConnectorSetResponse]:
    return [_to_set_response(item) for item in list_vendor_connector_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/vendor-connectors/records/{vendor_connector_id}", response_model=VendorConnectorRecordResponse)
def get_vendor_connector_record_route(vendor_connector_id: str, session: DBSession) -> VendorConnectorRecordResponse:
    return _to_record_response(get_vendor_connector_record(session, vendor_connector_id))
