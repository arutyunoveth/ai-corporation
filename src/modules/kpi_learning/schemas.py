from datetime import datetime

from pydantic import Field

from src.shared.enums import KPIStatus, LearningNoteType
from src.shared.types.common import APIModel


class LearningNoteInput(APIModel):
    note_type: LearningNoteType
    note_text: str


class BuildKPILearningRequest(APIModel):
    deal_id: str
    deal_closure_set_id: str
    learning_notes: list[LearningNoteInput] = Field(default_factory=list)


class LearningNoteRecordResponse(APIModel):
    learning_note_id: str
    kpi_learning_id: str
    note_type: LearningNoteType
    note_text: str
    created_at: datetime


class KPILearningRecordResponse(APIModel):
    kpi_learning_id: str
    kpi_learning_set_id: str
    cycle_time_days: float | None
    margin_estimate: float | None
    supplier_count: int
    incident_count: int
    payment_collection_days: float | None
    created_at: datetime
    updated_at: datetime
    learning_notes: list[LearningNoteRecordResponse]


class KPILearningSetResponse(APIModel):
    kpi_learning_set_id: str
    deal_id: str
    deal_closure_set_id: str
    kpi_status: KPIStatus
    created_at: datetime
    updated_at: datetime
    records: list[KPILearningRecordResponse]
