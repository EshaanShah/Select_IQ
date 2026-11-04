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


SIGNAL_NAMES = ("prompt_relevance", "ai_guidance", "preference")


@dataclass(frozen=True, slots=True)
class PhotoSignals:
    """Per-photo ranking evidence: A-03 brief relevance, A-04 guidance, A-06 preference."""

    photo_id: str
    prompt_relevance: float | None = None
    ai_guidance: float | None = None
    preference: float | None = None


@dataclass(frozen=True, slots=True)
class SignalProvenance:
    """Which models produced a proposal's signals, so test or fallback runs never pass as AI."""

    embedding_model: str
    embeddings_genuine: bool
    guidance_model: str | None
    guidance_status: str  # completed, failed, not_started
    guidance_genuine: bool
    comparisons_used: int
    preference_method: str
    excluded_photo_count: int = 0

    @property
    def kind(self) -> str:
        if not self.embeddings_genuine:
            return "test_signals"
        if self.guidance_genuine and self.guidance_status == "completed":
            return "ai_informed"
        return "partial_ai"

    @property
    def is_genuine_ai(self) -> bool:
        return self.kind == "ai_informed"

    @property
    def label(self) -> str:
        choices = _choices_phrase(self.comparisons_used)
        kind = self.kind
        if kind == "ai_informed":
            return (
                f"AI-informed proposal: {self.embedding_model} brief relevance, "
                f"{self.guidance_model} guidance, and {choices}."
            )
        if kind == "partial_ai":
            if self.guidance_status == "completed":
                reason = f"guidance came from the offline stand-in {self.guidance_model}"
            else:
                reason = "AI interpretation unavailable — using basic relevance"
            return f"Partially AI-informed: {self.embedding_model} brief relevance and {choices}; {reason}."
        return (
            f"Test signals (not AI): {self.embedding_model} encoder and "
            f"{self.guidance_model or 'no'} reasoner with {choices}."
        )


def _choices_phrase(count: int) -> str:
    if count == 0:
        return "no saved choices"
    return f"{count} saved choice{'' if count == 1 else 's'}"


@dataclass(frozen=True, slots=True)
class ProposalItem:
    photo_id: str
    original_filename: str
    rank: int
    score: float
    contributions: dict[str, float]
    removed: bool = False


@dataclass(frozen=True, slots=True)
class Proposal:
    id: str
    project_id: str
    version: int
    target_count: int
    provenance: SignalProvenance
    parameters: dict[str, object]
    items: tuple[ProposalItem, ...]
    created_at: datetime | None = None

    @property
    def selected(self) -> tuple[ProposalItem, ...]:
        return tuple(item for item in self.items if not item.removed)

    @property
    def removed_count(self) -> int:
        return len(self.items) - len(self.selected)


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

