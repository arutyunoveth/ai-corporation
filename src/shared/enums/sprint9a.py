from enum import StrEnum


class VendorProfileStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class VendorStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISABLED = "DISABLED"


class CapabilityStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    LIMITED = "LIMITED"
    UNSUPPORTED = "UNSUPPORTED"


class ActionConsoleStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class ActionConsoleItemType(StrEnum):
    QUEUE = "QUEUE"
    TASK = "TASK"
    SESSION = "SESSION"
    EXECUTION = "EXECUTION"
    ALERT = "ALERT"
    OTHER = "OTHER"


class ActionConsolePriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExternalGatewayStatus(StrEnum):
    BUILT = "BUILT"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    STALE = "STALE"


class GatewayActionType(StrEnum):
    SEND = "SEND"
    SYNC = "SYNC"
    EXPORT = "EXPORT"
    FOLLOW_UP = "FOLLOW_UP"
    OTHER = "OTHER"


class ExternalExecutionStatus(StrEnum):
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
