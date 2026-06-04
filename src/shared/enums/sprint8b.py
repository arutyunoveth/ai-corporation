from enum import StrEnum


class IntegrationTaskStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"
    READY = "READY"


class IntegrationTaskType(StrEnum):
    EMAIL_SEND = "EMAIL_SEND"
    SYNC_PULL = "SYNC_PULL"
    SYNC_PUSH = "SYNC_PUSH"
    FOLLOW_UP = "FOLLOW_UP"
    EXPORT = "EXPORT"
    OTHER = "OTHER"


class IntegrationTaskBindingType(StrEnum):
    QUEUE = "QUEUE"
    CONNECTOR = "CONNECTOR"
    WORKSPACE = "WORKSPACE"
    OTHER = "OTHER"


class OperatorSessionStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    STALE = "STALE"


class OperatorSessionItemType(StrEnum):
    QUEUE_ITEM = "QUEUE_ITEM"
    TASK = "TASK"
    ALERT = "ALERT"
    DECISION = "DECISION"
    OTHER = "OTHER"


class OperatorSessionItemStatus(StrEnum):
    VISIBLE = "VISIBLE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    HIDDEN = "HIDDEN"
    DONE = "DONE"


class ExecutionLedgerStatus(StrEnum):
    BUILT = "BUILT"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    STALE = "STALE"


class ExecutionStatus(StrEnum):
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
