from enum import StrEnum


class ContractRiskStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class ContractClauseType(StrEnum):
    PAYMENT = "PAYMENT"
    ACCEPTANCE = "ACCEPTANCE"
    PENALTY = "PENALTY"
    WARRANTY = "WARRANTY"
    DELIVERY = "DELIVERY"
    OTHER = "OTHER"


class RiskSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IntegratedRiskMemoStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class RiskSourceType(StrEnum):
    TECH = "TECH"
    SUPPLIER = "SUPPLIER"
    QUOTE = "QUOTE"
    FINANCE = "FINANCE"
    CONTRACT = "CONTRACT"


class ApprovalStatus(StrEnum):
    OPEN = "OPEN"
    DECIDED = "DECIDED"
    STALE = "STALE"


class ApprovalDecision(StrEnum):
    GO = "GO"
    GO_WITH_CONDITIONS = "GO_WITH_CONDITIONS"
    NO_GO = "NO_GO"
    NEEDS_REVIEW = "NEEDS_REVIEW"
