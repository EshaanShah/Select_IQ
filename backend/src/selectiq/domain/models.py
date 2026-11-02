from dataclasses import dataclass, field
from pathlib import Path

from selectiq.domain.enums import ProcessingState, RecommendationGroup


@dataclass(frozen=True, slots=True)
class Photograph:
    id: str
    project_id: str
    original_filename: str
    working_path: Path
    state: ProcessingState = ProcessingState.PENDING


@dataclass(frozen=True, slots=True)
class CreativeBrief:
    project_id: str
    original_text: str


@dataclass(frozen=True, slots=True)
class ComparisonChoice:
    project_id: str
    winner_id: str
    loser_id: str
    sequence: int
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Recommendation:
    photo_id: str
    group: RecommendationGroup
    explanation: str | None = None


@dataclass(slots=True)
class Project:
    id: str
    target_count: int | None = None
    brief: CreativeBrief | None = None
    photos: list[Photograph] = field(default_factory=list)

