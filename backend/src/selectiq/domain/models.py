from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from selectiq.domain.enums import ProcessingState, RecommendationGroup


@dataclass(frozen=True, slots=True)
class Photograph:
    id: str
    project_id: str
    original_filename: str
    working_path: Path
    content_hash: str
    width: int
    height: int
    byte_size: int
    state: ProcessingState = ProcessingState.PENDING
    analysis_error_code: str | None = None
    analysis_error_message: str | None = None


@dataclass(frozen=True, slots=True)
class PhotoFeature:
    photo_id: str
    model_name: str
    checkpoint: str
    model_fingerprint: str
    embedding_dimension: int
    embedding_path: Path
    prompt_hash: str | None = None
    brief_relevance: float | None = None


@dataclass(frozen=True, slots=True)
class PhotoNote:
    photo_id: str
    effect: str  # "boost" or "penalize"
    reason: str


@dataclass(frozen=True, slots=True)
class GuidedScore:
    photo_id: str
    guided_score: float
    descriptor_score: float
    note_adjustment: float
    brief_relevance: float | None
    explanation: str


@dataclass(frozen=True, slots=True)
class BriefInterpretation:
    """One auditable generative-model interpretation attempt for a project's brief."""

    id: str
    project_id: str
    prompt_hash: str
    status: str  # "completed" or "failed"
    provider: str
    model_name: str
    provider_called: bool
    summary: str | None = None
    positive_descriptors: tuple[str, ...] = ()
    negative_descriptors: tuple[str, ...] = ()
    photo_notes: tuple[PhotoNote, ...] = ()
    raw_response: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ImportFailure:
    filename: str
    code: str
    message: str
    created_at: datetime | None = None


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

