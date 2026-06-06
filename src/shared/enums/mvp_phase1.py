from enum import StrEnum


class AgentRegistryStatus(StrEnum):
    BUILT = "BUILT"
    FAILED = "FAILED"


class AgentActivationState(StrEnum):
    REVIEWED = "REVIEWED"
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


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
