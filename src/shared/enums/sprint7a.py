from enum import StrEnum


class DashboardScopeType(StrEnum):
    GLOBAL = "GLOBAL"
    DEAL = "DEAL"
    PIPELINE = "PIPELINE"
    EXECUTION = "EXECUTION"


class DashboardSnapshotStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class ArchiveExportStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"
    EXPORTED = "EXPORTED"


class ArchiveExportFormat(StrEnum):
    MANIFEST = "MANIFEST"
    ZIP_MANIFEST = "ZIP_MANIFEST"
    JSON_BUNDLE = "JSON_BUNDLE"
    OTHER = "OTHER"


class ArchiveExportItemRole(StrEnum):
    CORE_DOC = "CORE_DOC"
    EVIDENCE = "EVIDENCE"
    DECISION = "DECISION"
    FINANCE = "FINANCE"
    EXECUTION = "EXECUTION"
    OTHER = "OTHER"


class LearningAutomationScopeType(StrEnum):
    DEAL = "DEAL"
    PORTFOLIO = "PORTFOLIO"


class LearningAutomationStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"
    STALE = "STALE"


class LearningRecommendationType(StrEnum):
    PLAYBOOK = "PLAYBOOK"
    CHECKLIST = "CHECKLIST"
    RISK_PREVENTION = "RISK_PREVENTION"
    SUPPLIER_STRATEGY = "SUPPLIER_STRATEGY"
    PRICING_DISCIPLINE = "PRICING_DISCIPLINE"
    OTHER = "OTHER"
