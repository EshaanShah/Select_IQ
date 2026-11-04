"""Build a deterministic target-sized proposal from per-photo ranking signals (A-07).

Each signal is min-max normalized across the gallery so that differently scaled
inputs (A-03 CLIP brief relevance, A-04 guided scores, A-06 preference scores) can be
combined. A signal that is constant or missing for the whole gallery carries no
ranking information and contributes zero. The proposal is the top K by weighted
score; exact ties fall back to photo ID so fixed inputs always give one answer.

A photo's preference signal is only one weighted term, so losing a comparison
lowers its score without ever excluding it.
"""

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass

from selectiq.domain.errors import ValidationError
from selectiq.domain.models import SIGNAL_NAMES, PhotoSignals

__all__ = [
    "DEFAULT_WEIGHTS",
    "PhotoSignals",
    "RankedPhoto",
    "SignalWeights",
    "evidence_weighted",
    "propose",
]

PREFERENCE_WEIGHT_CEILING = 2.0
PREFERENCE_HALF_EVIDENCE = 5


@dataclass(frozen=True, slots=True)
class SignalWeights:
    prompt_relevance: float = 1.0
    ai_guidance: float = 1.0
    preference: float = 1.0

    def __post_init__(self) -> None:
        values = [getattr(self, name) for name in SIGNAL_NAMES]
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValidationError("Every signal weight must be a finite, non-negative number.")
        if sum(values) == 0:
            raise ValidationError("At least one signal weight must be positive.")

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


DEFAULT_WEIGHTS = SignalWeights()


def evidence_weighted(comparisons_used: int) -> SignalWeights:
    """Trust saved choices more as they accumulate (TDD 12.3).

    Five choices give preference the same weight as prompt relevance and AI guidance;
    the weight approaches PREFERENCE_WEIGHT_CEILING as evidence grows.
    """
    if comparisons_used < 0:
        raise ValidationError("Saved choices cannot be negative.")
    preference = PREFERENCE_WEIGHT_CEILING * comparisons_used / (
        comparisons_used + PREFERENCE_HALF_EVIDENCE
    )
    return SignalWeights(prompt_relevance=1.0, ai_guidance=1.0, preference=preference)


@dataclass(frozen=True, slots=True)
class RankedPhoto:
    photo_id: str
    rank: int
    score: float
    contributions: dict[str, float]


def propose(
    signals: Sequence[PhotoSignals],
    target_count: int,
    weights: SignalWeights = DEFAULT_WEIGHTS,
) -> list[RankedPhoto]:
    _validate(signals, target_count)
    normalized = {name: _normalize([getattr(s, name) for s in signals]) for name in SIGNAL_NAMES}

    scored: list[tuple[float, str, dict[str, float]]] = []
    for index, signal in enumerate(signals):
        contributions = {
            name: getattr(weights, name) * normalized[name][index] for name in SIGNAL_NAMES
        }
        scored.append((sum(contributions.values()), signal.photo_id, contributions))

    scored.sort(key=lambda entry: (-entry[0], entry[1]))
    return [
        RankedPhoto(photo_id=photo_id, rank=rank, score=score, contributions=contributions)
        for rank, (score, photo_id, contributions) in enumerate(scored[:target_count], start=1)
    ]


def _validate(signals: Sequence[PhotoSignals], target_count: int) -> None:
    if not signals:
        raise ValidationError("The project has no photographs to propose.")
    if len({signal.photo_id for signal in signals}) != len(signals):
        raise ValidationError("Photo IDs must be unique within a proposal.")
    if not 1 <= target_count <= len(signals):
        raise ValidationError(f"Target must be between 1 and {len(signals)} photographs.")
    for signal in signals:
        for name in SIGNAL_NAMES:
            value = getattr(signal, name)
            if value is not None and not math.isfinite(value):
                raise ValidationError(f"Signal {name} for photo {signal.photo_id} must be finite.")


def _normalize(values: list[float | None]) -> list[float]:
    present = [value for value in values if value is not None]
    if not present:
        return [0.0] * len(values)
    low, high = min(present), max(present)
    if high == low:
        return [0.0] * len(values)
    return [0.0 if value is None else (value - low) / (high - low) for value in values]
