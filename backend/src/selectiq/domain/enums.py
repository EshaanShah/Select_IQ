from enum import StrEnum


class ProcessingState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TechnicalIntent(StrEnum):
    AVOID = "avoid"
    NEUTRAL = "neutral"
    ACCEPT = "accept"
    PREFER = "prefer"


class RecommendationGroup(StrEnum):
    REGULAR = "regular"
    UNCERTAIN = "uncertain"

