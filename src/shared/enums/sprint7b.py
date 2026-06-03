from enum import StrEnum


class WorkflowScopeType(StrEnum):
    DEAL = "DEAL"
    PIPELINE = "PIPELINE"
    EXECUTION = "EXECUTION"
    PORTFOLIO = "PORTFOLIO"


class WorkflowStatus(StrEnum):
    BUILT = "BUILT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STALE = "STALE"


class WorkflowStepType(StrEnum):
    CHECK = "CHECK"
    BUILD = "BUILD"
    REVIEW = "REVIEW"
    FOLLOW_UP = "FOLLOW_UP"
    ESCALATE = "ESCALATE"
    CLOSE = "CLOSE"
    OTHER = "OTHER"


class WorkflowStepStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


class OptimizationScopeType(StrEnum):
    DEAL = "DEAL"
    PORTFOLIO = "PORTFOLIO"
    SUPPLIER = "SUPPLIER"
    PROCESS = "PROCESS"


class OptimizationStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class OptimizationRecommendationType(StrEnum):
    CYCLE_TIME = "CYCLE_TIME"
    MARGIN = "MARGIN"
    RISK_REDUCTION = "RISK_REDUCTION"
    SUPPLIER_STRATEGY = "SUPPLIER_STRATEGY"
    PROCESS_DISCIPLINE = "PROCESS_DISCIPLINE"
    OTHER = "OTHER"


class CopilotFeedStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class CopilotFeedItemType(StrEnum):
    ACTION = "ACTION"
    ALERT = "ALERT"
    RECOMMENDATION = "RECOMMENDATION"
    REMINDER = "REMINDER"
    FOLLOW_UP = "FOLLOW_UP"
    OTHER = "OTHER"


class CopilotPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
