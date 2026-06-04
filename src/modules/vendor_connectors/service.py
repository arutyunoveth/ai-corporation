from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.connector_registry.models import ConnectorRegistryRecord, ConnectorRegistrySet
from src.modules.event_log.service import append_event_record
from src.modules.vendor_connectors.models import (
    VendorConnectorCapability,
    VendorConnectorRecord,
    VendorConnectorSet,
)
from src.modules.vendor_connectors.schemas import BuildVendorConnectorProfilesRequest
from src.shared.control_package import ensure_scope_exists, latest_connector_registry_context, resolve_scope_deal_id
from src.shared.db.base import utcnow
from src.shared.enums import (
    CapabilityStatus,
    ConnectorScopeType,
    ConnectorStatus,
    ConnectorType,
    EventSeverity,
    VendorProfileStatus,
    VendorStatus,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import (
    next_vendor_connector_id,
    next_vendor_connector_set_id,
)


def _get_set(session: Session, vendor_connector_set_id: str) -> VendorConnectorSet:
    record = session.scalar(
        select(VendorConnectorSet).where(VendorConnectorSet.vendor_connector_set_id == vendor_connector_set_id)
    )
    if not record:
        raise NotFoundError(f"Vendor connector set '{vendor_connector_set_id}' was not found")
    return record


def _get_record(session: Session, vendor_connector_id: str) -> VendorConnectorRecord:
    record = session.scalar(
        select(VendorConnectorRecord).where(VendorConnectorRecord.vendor_connector_id == vendor_connector_id)
    )
    if not record:
        raise NotFoundError(f"Vendor connector record '{vendor_connector_id}' was not found")
    return record


def _get_records(session: Session, vendor_connector_set_id: str) -> list[VendorConnectorRecord]:
    return list(
        session.scalars(
            select(VendorConnectorRecord)
            .where(VendorConnectorRecord.vendor_connector_set_id == vendor_connector_set_id)
            .order_by(VendorConnectorRecord.created_at.asc(), VendorConnectorRecord.id.asc())
        )
    )


def _get_capabilities(session: Session, vendor_connector_id: str) -> list[VendorConnectorCapability]:
    return list(
        session.scalars(
            select(VendorConnectorCapability)
            .where(VendorConnectorCapability.vendor_connector_id == vendor_connector_id)
            .order_by(VendorConnectorCapability.created_at.asc(), VendorConnectorCapability.id.asc())
        )
    )


def _vendor_code(record: ConnectorRegistryRecord) -> str:
    if record.connector_type == ConnectorType.EMAIL:
        return "EMAIL_GATEWAY"
    if record.connector_type == ConnectorType.PORTAL:
        return "PROCUREMENT_PORTAL_GATEWAY"
    if record.connector_type == ConnectorType.CRM:
        return "CRM_ADAPTER"
    if record.connector_type == ConnectorType.DRIVE:
        return "DOCUMENT_EXPORT_GATEWAY"
    if record.connector_type == ConnectorType.SHEETS:
        return "SHEETS_EXPORT_GATEWAY"
    return f"{record.connector_code}_VENDOR"


def _vendor_status(record: ConnectorRegistryRecord) -> VendorStatus:
    if record.connector_status == ConnectorStatus.ACTIVE:
        return VendorStatus.ACTIVE
    if record.connector_status == ConnectorStatus.DISABLED:
        return VendorStatus.DISABLED
    return VendorStatus.INACTIVE


def _capability_specs(record: ConnectorRegistryRecord) -> list[dict]:
    if record.connector_type == ConnectorType.EMAIL:
        return [
            {"capability_code": "SEND", "capability_status": CapabilityStatus.SUPPORTED, "notes": "Email delivery is available."},
            {"capability_code": "FOLLOW_UP", "capability_status": CapabilityStatus.SUPPORTED, "notes": "Follow-up reminders can be sent."},
            {"capability_code": "EXPORT", "capability_status": CapabilityStatus.LIMITED, "notes": "Attachments are optional and limited."},
        ]
    if record.connector_type == ConnectorType.PORTAL:
        return [
            {"capability_code": "SYNC", "capability_status": CapabilityStatus.SUPPORTED, "notes": "Portal sync is available."},
            {"capability_code": "SEND", "capability_status": CapabilityStatus.LIMITED, "notes": "Submission actions stay controlled and narrow."},
            {"capability_code": "FOLLOW_UP", "capability_status": CapabilityStatus.LIMITED, "notes": "Portal follow-up is supported only for tracked tenders."},
        ]
    if record.connector_type == ConnectorType.CRM:
        return [
            {"capability_code": "SYNC", "capability_status": CapabilityStatus.SUPPORTED, "notes": "CRM synchronization is the primary flow."},
            {"capability_code": "EXPORT", "capability_status": CapabilityStatus.LIMITED, "notes": "Export is available through CRM data extracts."},
            {"capability_code": "SEND", "capability_status": CapabilityStatus.UNSUPPORTED, "notes": "Direct outbound execution is not supported."},
        ]
    if record.connector_type == ConnectorType.DRIVE:
        return [
            {"capability_code": "EXPORT", "capability_status": CapabilityStatus.SUPPORTED, "notes": "Document export is supported."},
            {"capability_code": "SYNC", "capability_status": CapabilityStatus.LIMITED, "notes": "Inbound sync is metadata-oriented."},
            {"capability_code": "SEND", "capability_status": CapabilityStatus.UNSUPPORTED, "notes": "Drive does not send actions directly."},
        ]
    if record.connector_type == ConnectorType.SHEETS:
        return [
            {"capability_code": "EXPORT", "capability_status": CapabilityStatus.SUPPORTED, "notes": "Spreadsheet exports are supported."},
            {"capability_code": "SYNC", "capability_status": CapabilityStatus.LIMITED, "notes": "Sheet sync is supported with reduced fidelity."},
            {"capability_code": "FOLLOW_UP", "capability_status": CapabilityStatus.UNSUPPORTED, "notes": "Sheets do not perform follow-up calls."},
        ]
    return [{"capability_code": "OTHER", "capability_status": CapabilityStatus.LIMITED, "notes": "Generic connector capability profile."}]


def build_vendor_connector_profiles(
    session: Session,
    payload: BuildVendorConnectorProfilesRequest,
) -> VendorConnectorSet:
    if payload.scope_type in {ConnectorScopeType.DEAL, ConnectorScopeType.EXECUTION}:
        ensure_scope_exists(session, payload.scope_type, payload.scope_ref)
    connector_set, connectors = latest_connector_registry_context(session, payload.scope_type, payload.scope_ref)
    vendor_set = VendorConnectorSet(
        vendor_connector_set_id=next_vendor_connector_set_id(session, VendorConnectorSet.vendor_connector_set_id),
        scope_type=payload.scope_type,
        scope_ref=payload.scope_ref,
        profile_status=VendorProfileStatus.BUILT,
    )
    session.add(vendor_set)
    session.flush()
    deal_id = resolve_scope_deal_id(session, payload.scope_type, payload.scope_ref)
    try:
        if not connector_set or not connectors:
            raise ValidationError("Vendor connector profiles require persisted connector registry context")
        for connector in connectors:
            record = VendorConnectorRecord(
                vendor_connector_id=next_vendor_connector_id(session, VendorConnectorRecord.vendor_connector_id),
                vendor_connector_set_id=vendor_set.vendor_connector_set_id,
                connector_registry_id=connector.connector_registry_id,
                vendor_code=_vendor_code(connector),
                vendor_status=_vendor_status(connector),
            )
            session.add(record)
            session.flush()
            for capability in _capability_specs(connector):
                session.add(
                    VendorConnectorCapability(
                        vendor_connector_id=record.vendor_connector_id,
                        **capability,
                    )
                )
                session.flush()
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="vendor_connector_profile_built",
            source_module_id="M-060",
            severity=EventSeverity.INFO,
            payload_json={
                "vendor_connector_set_id": vendor_set.vendor_connector_set_id,
                "connector_registry_set_id": connector_set.connector_registry_set_id,
                "connector_count": len(connectors),
            },
        )
        session.commit()
        session.refresh(vendor_set)
        return vendor_set
    except Exception as exc:
        vendor_set.profile_status = VendorProfileStatus.FAILED
        vendor_set.updated_at = utcnow()
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="vendor_connector_profile_failed",
            source_module_id="M-060",
            severity=EventSeverity.HIGH,
            payload_json={"vendor_connector_set_id": vendor_set.vendor_connector_set_id, "error": str(exc)},
        )
        session.commit()
        raise


def get_vendor_connector_set(
    session: Session,
    vendor_connector_set_id: str,
) -> tuple[VendorConnectorSet, list[tuple[VendorConnectorRecord, list[VendorConnectorCapability]]]]:
    vendor_set = _get_set(session, vendor_connector_set_id)
    records = [
        (record, _get_capabilities(session, record.vendor_connector_id))
        for record in _get_records(session, vendor_connector_set_id)
    ]
    return vendor_set, records


def get_vendor_connector_record(
    session: Session,
    vendor_connector_id: str,
) -> tuple[VendorConnectorRecord, list[VendorConnectorCapability]]:
    record = _get_record(session, vendor_connector_id)
    return record, _get_capabilities(session, record.vendor_connector_id)


def list_vendor_connector_sets(
    session: Session,
    *,
    scope_type: ConnectorScopeType | None = None,
    scope_ref: str | None = None,
) -> list[tuple[VendorConnectorSet, list[tuple[VendorConnectorRecord, list[VendorConnectorCapability]]]]]:
    query = select(VendorConnectorSet).order_by(VendorConnectorSet.created_at.desc(), VendorConnectorSet.id.desc())
    if scope_type:
        query = query.where(VendorConnectorSet.scope_type == scope_type)
    if scope_ref:
        query = query.where(VendorConnectorSet.scope_ref == scope_ref)
    return [get_vendor_connector_set(session, item.vendor_connector_set_id) for item in session.scalars(query)]
