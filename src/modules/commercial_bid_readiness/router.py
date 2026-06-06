from fastapi import APIRouter, status

from src.modules.commercial_bid_readiness.schemas import (
    BuildCommercialBidReadinessRequest,
    BuildCommercialSupplierRequestDraftRequest,
    CommercialBidWorkspaceActionRequest,
    CommercialBidWorkspaceActionResponse,
    CommercialManualTKPBatchResponse,
    CommercialSupplierRequestDraftResponse,
    CommercialWorkspaceSnapshotResponse,
    RegisterCommercialTKPBatchRequest,
)
from src.modules.commercial_bid_readiness.service import (
    build_commercial_bid_readiness,
    build_supplier_request_draft,
    get_commercial_workspace_snapshot,
    record_commercial_workspace_action,
    register_manual_tkp_batch,
)
from src.shared.api.dependencies import DBSession


router = APIRouter(tags=["commercial-bid-readiness"])


@router.post(
    "/commercial-workspace/{deal_id}/supplier-request-draft",
    response_model=CommercialSupplierRequestDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def commercial_supplier_request_draft(
    deal_id: str,
    payload: BuildCommercialSupplierRequestDraftRequest,
    session: DBSession,
) -> CommercialSupplierRequestDraftResponse:
    return build_supplier_request_draft(session, deal_id, payload)


@router.post(
    "/commercial-workspace/{deal_id}/tkp/register-manual-batch",
    response_model=CommercialManualTKPBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
def commercial_register_manual_tkp_batch(
    deal_id: str,
    payload: RegisterCommercialTKPBatchRequest,
    session: DBSession,
) -> CommercialManualTKPBatchResponse:
    return register_manual_tkp_batch(session, deal_id, payload)


@router.post(
    "/commercial-workspace/{deal_id}/readiness/build",
    response_model=CommercialWorkspaceSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def commercial_build_bid_readiness(
    deal_id: str,
    payload: BuildCommercialBidReadinessRequest,
    session: DBSession,
) -> CommercialWorkspaceSnapshotResponse:
    return build_commercial_bid_readiness(session, deal_id, payload)


@router.get(
    "/commercial-workspace/{deal_id}",
    response_model=CommercialWorkspaceSnapshotResponse,
)
def commercial_workspace_snapshot(
    deal_id: str,
    session: DBSession,
) -> CommercialWorkspaceSnapshotResponse:
    return get_commercial_workspace_snapshot(session, deal_id)


@router.post(
    "/commercial-workspace/{deal_id}/actions",
    response_model=CommercialBidWorkspaceActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def commercial_workspace_action(
    deal_id: str,
    payload: CommercialBidWorkspaceActionRequest,
    session: DBSession,
) -> CommercialBidWorkspaceActionResponse:
    return record_commercial_workspace_action(session, deal_id, payload)
