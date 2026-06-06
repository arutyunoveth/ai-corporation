from fastapi import APIRouter, status

from src.modules.commercial_prebid_demo.schemas import (
    CommercialPreBidDemoResponse,
    RunCommercialPreBidDemoRequest,
)
from src.modules.commercial_prebid_demo.service import run_commercial_prebid_demo
from src.shared.api.dependencies import DBSession


router = APIRouter(tags=["commercial-prebid-demo"])


@router.post(
    "/commercial-prebid-demo/run",
    response_model=CommercialPreBidDemoResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_commercial_prebid_demo_route(
    payload: RunCommercialPreBidDemoRequest,
    session: DBSession,
) -> CommercialPreBidDemoResponse:
    return run_commercial_prebid_demo(session, payload)
