from fastapi import APIRouter, Query, status

from src.modules.runtime_control_traces.schemas import (
    CreateRuntimeControlTraceRequest,
    RuntimeControlTraceResponse,
    UpdateRuntimeControlTraceReviewRequest,
)
from src.modules.runtime_control_traces.service import (
    create_runtime_control_trace,
    get_runtime_control_trace,
    list_runtime_control_traces,
    update_runtime_control_trace_review,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["runtime-control-traces"])


def _to_response(trace) -> RuntimeControlTraceResponse:
    return RuntimeControlTraceResponse.model_validate(trace)


@router.post(
    "/runtime-control-traces",
    response_model=RuntimeControlTraceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_runtime_control_trace_route(
    payload: CreateRuntimeControlTraceRequest,
    session: DBSession,
) -> RuntimeControlTraceResponse:
    return _to_response(create_runtime_control_trace(session, payload))


@router.get("/runtime-control-traces/{runtime_trace_id}", response_model=RuntimeControlTraceResponse)
def get_runtime_control_trace_route(
    runtime_trace_id: str,
    session: DBSession,
) -> RuntimeControlTraceResponse:
    return _to_response(get_runtime_control_trace(session, runtime_trace_id))


@router.get("/runtime-control-traces", response_model=list[RuntimeControlTraceResponse])
def list_runtime_control_traces_route(
    session: DBSession,
    runtime_slice: str | None = Query(default=None),
) -> list[RuntimeControlTraceResponse]:
    return [_to_response(item) for item in list_runtime_control_traces(session, runtime_slice=runtime_slice)]


@router.patch(
    "/runtime-control-traces/{runtime_trace_id}/review-status",
    response_model=RuntimeControlTraceResponse,
)
def update_runtime_control_trace_review_route(
    runtime_trace_id: str,
    payload: UpdateRuntimeControlTraceReviewRequest,
    session: DBSession,
) -> RuntimeControlTraceResponse:
    return _to_response(update_runtime_control_trace_review(session, runtime_trace_id, payload))
