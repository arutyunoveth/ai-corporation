from enum import StrEnum


class SubmissionExecutionStatus(StrEnum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SubmissionAttemptStatus(StrEnum):
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class SubmissionChannelType(StrEnum):
    MANUAL = "MANUAL"
    PORTAL = "PORTAL"
    API = "API"
    OTHER = "OTHER"


class SubmissionReceiptStatus(StrEnum):
    REGISTERED = "REGISTERED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class ReceiptSourceType(StrEnum):
    PORTAL = "PORTAL"
    EMAIL = "EMAIL"
    MANUAL = "MANUAL"
    OTHER = "OTHER"


class ReceiptBindingType(StrEnum):
    SCREENSHOT = "SCREENSHOT"
    PDF = "PDF"
    EMAIL = "EMAIL"
    OTHER = "OTHER"


class PostSubmissionTrackerStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    STALE = "STALE"


class PostSubmissionStage(StrEnum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLARIFICATION = "CLARIFICATION"
    AWARDED = "AWARDED"
    LOST = "LOST"
    CANCELLED = "CANCELLED"
    OTHER = "OTHER"


class PostSubmissionEventType(StrEnum):
    STATUS_UPDATE = "STATUS_UPDATE"
    CLARIFICATION = "CLARIFICATION"
    REQUEST = "REQUEST"
    NOTICE = "NOTICE"
    OTHER = "OTHER"


class OutcomeStatus(StrEnum):
    RECORDED = "RECORDED"
    REVISED = "REVISED"
    FAILED = "FAILED"


class OutcomeCode(StrEnum):
    WON = "WON"
    LOST = "LOST"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    NO_RESULT = "NO_RESULT"


class OutcomeBindingType(StrEnum):
    NOTICE = "NOTICE"
    PROTOCOL = "PROTOCOL"
    EMAIL = "EMAIL"
    OTHER = "OTHER"
