from datetime import datetime

from src.shared.enums import (
    OperatorSessionItemStatus,
    OperatorSessionItemType,
    OperatorSessionStatus,
    WorkspaceScopeType,
)
from src.shared.types.common import APIModel


class BuildOperatorSessionRequest(APIModel):
    scope_type: WorkspaceScopeType
    scope_ref: str
    opened_by_ref: str


class AcknowledgeOperatorSessionItemRequest(APIModel):
    operator_session_id: str
    item_code: str
    source_ref: str | None = None


class OperatorSessionItemResponse(APIModel):
    item_code: str
    item_type: OperatorSessionItemType
    source_ref: str | None
    item_status: OperatorSessionItemStatus
    created_at: datetime
    updated_at: datetime


class OperatorSessionRecordResponse(APIModel):
    operator_session_id: str
    operator_session_set_id: str
    opened_by_ref: str
    summary_text: str
    created_at: datetime
    updated_at: datetime
    items: list[OperatorSessionItemResponse]


class OperatorSessionSetResponse(APIModel):
    operator_session_set_id: str
    scope_type: WorkspaceScopeType
    scope_ref: str
    session_status: OperatorSessionStatus
    created_at: datetime
    updated_at: datetime
    records: list[OperatorSessionRecordResponse]
