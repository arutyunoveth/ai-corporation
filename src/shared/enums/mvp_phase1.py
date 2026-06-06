from enum import StrEnum


class AgentRegistryStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"


class AgentLifecycleStatus(StrEnum):
    REVIEWED = "REVIEWED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class AgentActivationState(StrEnum):
    REVIEWED = "REVIEWED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class HumanReviewStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_VALIDATION = "needs_validation"
    VALIDATION_FAILED = "validation_failed"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    APPROVED_FOR_INTERNAL_USE = "approved_for_internal_use"
    APPROVED_FOR_EXTERNAL_USE = "approved_for_external_use"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class PromptSchemaLibraryStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"


class PromptSchemaAssetStatus(StrEnum):
    REVIEWED = "REVIEWED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class PromptSchemaAssetType(StrEnum):
    PROMPT_TEMPLATE = "PROMPT_TEMPLATE"
    INPUT_SCHEMA = "INPUT_SCHEMA"
    OUTPUT_SCHEMA = "OUTPUT_SCHEMA"
    COMPOSITE = "COMPOSITE"


class AgentPromptLinkStatus(StrEnum):
    APPROVED = "APPROVED"
    DISABLED = "DISABLED"
