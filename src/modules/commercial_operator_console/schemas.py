from typing import Literal

from pydantic import Field

from src.shared.types.common import APIModel


class CommercialOperatorActionRequest(APIModel):
    action: Literal["rejected", "needs_more_review", "collect_tkp", "prepare_bid_draft"]
    operator_ref: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class CommercialOperatorActionResponse(APIModel):
    deal_id: str
    action: str
    decision_id: str
    recorded_event_id: str
