from enum import StrEnum


class CostModelStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class CostLineType(StrEnum):
    BASE_QUOTE = "BASE_QUOTE"
    LOGISTICS = "LOGISTICS"
    BUFFER = "BUFFER"
    OVERHEAD = "OVERHEAD"
    OTHER = "OTHER"


class CashGapStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class FinancingStrategyStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class FinancingFeasibilityStatus(StrEnum):
    FEASIBLE = "FEASIBLE"
    LIMITED = "LIMITED"
    INFEASIBLE = "INFEASIBLE"


class FinanceMemoStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class FinanceRecommendation(StrEnum):
    GO = "GO"
    GO_WITH_CONDITIONS = "GO_WITH_CONDITIONS"
    NO_GO = "NO_GO"
    NEEDS_REVIEW = "NEEDS_REVIEW"
