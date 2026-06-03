from enum import StrEnum


class TenderSourceType(StrEnum):
    PORTAL = "PORTAL"
    EMAIL = "EMAIL"
    MANUAL = "MANUAL"
    API = "API"
    OTHER = "OTHER"


class IntakeStatus(StrEnum):
    RECEIVED = "RECEIVED"
    NORMALIZED = "NORMALIZED"
    LINKED = "LINKED"
    FAILED = "FAILED"


class DocumentSetType(StrEnum):
    TENDER_INITIAL = "TENDER_INITIAL"
    TENDER_REFRESH = "TENDER_REFRESH"
    OTHER = "OTHER"


class DocumentIngestionStatus(StrEnum):
    CREATED = "CREATED"
    INGESTED = "INGESTED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class DocumentIngestionRunStatus(StrEnum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class DocumentSetItemRole(StrEnum):
    NOTICE = "NOTICE"
    TZ = "TZ"
    DRAFT_CONTRACT = "DRAFT_CONTRACT"
    ATTACHMENT = "ATTACHMENT"
    OTHER = "OTHER"


class TenderSummaryStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"

