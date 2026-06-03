from enum import StrEnum


class ScreeningResultStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class PriorityBucket(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    REJECT = "REJECT"


class ComplianceStatus(StrEnum):
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class DocumentRequirementStatus(StrEnum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"


class TechRiskSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TechRiskCategory(StrEnum):
    AMBIGUITY = "AMBIGUITY"
    INCOMPLETE_SPEC = "INCOMPLETE_SPEC"
    BRAND_LOCK = "BRAND_LOCK"
    EQUIVALENCE_RISK = "EQUIVALENCE_RISK"
    TIMELINE_RISK = "TIMELINE_RISK"
    OTHER = "OTHER"

