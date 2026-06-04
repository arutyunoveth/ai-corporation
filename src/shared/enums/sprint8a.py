from enum import StrEnum


class ConnectorScopeType(StrEnum):
    GLOBAL = "GLOBAL"
    DEAL = "DEAL"
    PIPELINE = "PIPELINE"
    EXECUTION = "EXECUTION"


class ConnectorType(StrEnum):
    EMAIL = "EMAIL"
    PORTAL = "PORTAL"
    CRM = "CRM"
    DRIVE = "DRIVE"
    SHEETS = "SHEETS"
    OTHER = "OTHER"


class ConnectorRegistryStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class ConnectorStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DISABLED = "DISABLED"


class ConnectorSyncStatus(StrEnum):
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class WorkspaceScopeType(StrEnum):
    DEAL = "DEAL"
    PIPELINE = "PIPELINE"
    EXECUTION = "EXECUTION"
    PORTFOLIO = "PORTFOLIO"


class WorkspaceStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class WorkspaceItemType(StrEnum):
    TASK = "TASK"
    ALERT = "ALERT"
    SUGGESTION = "SUGGESTION"
    DECISION = "DECISION"
    FOLLOW_UP = "FOLLOW_UP"
    OTHER = "OTHER"


class WorkspacePriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionQueueStatus(StrEnum):
    BUILT = "BUILT"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    STALE = "STALE"


class ActionType(StrEnum):
    EMAIL_DRAFT = "EMAIL_DRAFT"
    FOLLOW_UP = "FOLLOW_UP"
    SYNC = "SYNC"
    REBUILD = "REBUILD"
    ESCALATE = "ESCALATE"
    OTHER = "OTHER"


class ActionExecutionStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


class QueueApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
