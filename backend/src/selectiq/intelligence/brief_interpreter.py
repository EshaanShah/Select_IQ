"""A-04: interpret a creative brief with a generative model and turn it into guided scores.

The generative model never ranks photographs directly. It returns short visual descriptors
and optional per-photo notes; descriptors are embedded with the same CLIP text encoder used
in A-03, and every photograph's guided score is an auditable sum of those similarities plus
a fixed note adjustment. Any failure is persisted as a failed interpretation and ranking
falls back to plain CLIP brief relevance.
"""

import hashlib
import json
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import uuid4

import numpy as np

from selectiq.domain.enums import ProcessingState
from selectiq.domain.models import BriefInterpretation, GuidedScore, Photograph, PhotoNote
from selectiq.infrastructure.contact_sheet import ContactSheetError, build_contact_sheets
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.model_adapters import VisualEncoder
from selectiq.infrastructure.project_repository import ProjectRepository
from selectiq.infrastructure.reasoners import BriefReasoner, ReasonerError, ReasonerRequest

NOTE_WEIGHT = 0.05
MAX_POSITIVE = 6
MAX_NEGATIVE = 4
MAX_DESCRIPTOR_WORDS = 12
MAX_DESCRIPTOR_CHARS = 100
MAX_SUMMARY_CHARS = 1000
MAX_REASON_CHARS = 400
EFFECTS = {"boost": NOTE_WEIGHT, "penalize": -NOTE_WEIGHT}


class InterpretationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ParsedInterpretation:
    summary: str
    positive_descriptors: tuple[str, ...]
    negative_descriptors: tuple[str, ...]
    photo_notes: tuple[PhotoNote, ...]


@dataclass(frozen=True, slots=True)
class RankingEntry:
    photo_id: str
    rank: int
    guided_score: float | None
    brief_relevance: float | None
    explanation: str | None


@dataclass(frozen=True, slots=True)
class Ranking:
    basis: str  # "guided" or "brief_relevance"
    entries: tuple[RankingEntry, ...]


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _strip_wrappers(raw: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    return fenced.group(1) if fenced else text


def _text(value: object, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InterpretationError("schema_violation", f"{field} must be a nonempty string.")
    text = " ".join(value.split())
    if len(text) > limit:
        raise InterpretationError("schema_violation", f"{field} exceeds {limit} characters.")
    return text


def _descriptors(value: object, field: str, minimum: int, maximum: int) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise InterpretationError("schema_violation", f"{field} must be a list.")
    seen: dict[str, str] = {}
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise InterpretationError("schema_violation", f"{field} entries must be strings.")
        text = " ".join(item.split())
        if len(text.split()) > MAX_DESCRIPTOR_WORDS or len(text) > MAX_DESCRIPTOR_CHARS:
            raise InterpretationError(
                "invalid_descriptor",
                f"Descriptor is too long for the CLIP text encoder: {text[:60]!r}.",
            )
        seen.setdefault(text.casefold(), text)
    descriptors = tuple(seen.values())
    if not minimum <= len(descriptors) <= maximum:
        raise InterpretationError(
            "schema_violation", f"{field} must contain {minimum}-{maximum} descriptors."
        )
    return descriptors


def parse_interpretation(raw: str, labels: Mapping[str, str]) -> ParsedInterpretation:
    """Validate a raw model completion; `labels` maps sheet labels (P01) to photo IDs."""
    try:
        body = json.loads(_strip_wrappers(raw or ""))
    except json.JSONDecodeError as error:
        raise InterpretationError("malformed_output", "The model did not return JSON.") from error
    if not isinstance(body, dict):
        raise InterpretationError("malformed_output", "The model did not return a JSON object.")
    required = {"summary", "positive_descriptors", "negative_descriptors", "photo_notes"}
    if missing := required - body.keys():
        raise InterpretationError(
            "schema_violation", f"Missing fields: {', '.join(sorted(missing))}."
        )
    summary = _text(body["summary"], "summary", MAX_SUMMARY_CHARS)
    positive = _descriptors(body["positive_descriptors"], "positive_descriptors", 1, MAX_POSITIVE)
    negative = _descriptors(body["negative_descriptors"], "negative_descriptors", 0, MAX_NEGATIVE)

    notes_value = body["photo_notes"]
    if not isinstance(notes_value, list):
        raise InterpretationError("schema_violation", "photo_notes must be a list.")
    notes: list[PhotoNote] = []
    for note in notes_value:
        if not isinstance(note, dict) or not {"label", "effect", "reason"} <= note.keys():
            raise InterpretationError(
                "schema_violation", "Each photo note needs a label, effect, and reason."
            )
        label = note["label"]
        if not isinstance(label, str):
            raise InterpretationError("schema_violation", "Photo note labels must be strings.")
        label = label.strip().upper()
        if label not in labels:
            raise InterpretationError(
                "unknown_photo_id", f"The model referenced a photograph that does not exist: {label}."
            )
        if note["effect"] not in EFFECTS:
            raise InterpretationError("schema_violation", "Photo note effect must be boost or penalize.")
        photo_id = labels[label]
        if any(existing.photo_id == photo_id for existing in notes):
            raise InterpretationError("schema_violation", f"{label} has more than one note.")
        notes.append(PhotoNote(photo_id, note["effect"], _text(note["reason"], "reason", MAX_REASON_CHARS)))
    return ParsedInterpretation(summary, positive, negative, tuple(notes))


def compute_guided_scores(
    image_vectors: Mapping[str, np.ndarray],
    positive: Sequence[tuple[str, np.ndarray]],
    negative: Sequence[tuple[str, np.ndarray]],
    notes: Sequence[PhotoNote],
    brief_relevance: Mapping[str, float | None],
) -> list[GuidedScore]:
    """guided = mean(sim to positives) - mean(sim to negatives) + note adjustment."""
    notes_by_photo = {note.photo_id: note for note in notes}
    scores: list[GuidedScore] = []
    for photo_id, vector in image_vectors.items():
        positive_sims = [(text, float(vector @ v)) for text, v in positive]
        negative_sims = [(text, float(vector @ v)) for text, v in negative]
        descriptor_score = float(np.mean([s for _, s in positive_sims])) - (
            float(np.mean([s for _, s in negative_sims])) if negative_sims else 0.0
        )
        note = notes_by_photo.get(photo_id)
        adjustment = EFFECTS[note.effect] if note else 0.0
        best_text, best_sim = max(positive_sims, key=lambda item: item[1])
        parts = [f"Closest to “{best_text}” ({best_sim:.3f})"]
        if negative_sims:
            worst_text, worst_sim = max(negative_sims, key=lambda item: item[1])
            parts.append(f"avoid “{worst_text}” ({worst_sim:.3f})")
        explanation = "; ".join(parts) + "."
        if note:
            explanation += f" Model {note.effect}: {note.reason}"
        scores.append(
            GuidedScore(
                photo_id=photo_id,
                guided_score=descriptor_score + adjustment,
                descriptor_score=descriptor_score,
                note_adjustment=adjustment,
                brief_relevance=brief_relevance.get(photo_id),
                explanation=explanation,
            )
        )
    scores.sort(key=lambda score: (-score.guided_score, score.photo_id))
    return scores


class BriefInterpreter:
    def __init__(
        self,
        repository: ProjectRepository,
        cache: NumpyEmbeddingCache,
        encoder: VisualEncoder,
        reasoner: BriefReasoner,
        max_provider_calls: int = 20,
    ) -> None:
        self.repository = repository
        self.cache = cache
        self.encoder = encoder
        self.reasoner = reasoner
        self.max_provider_calls = max_provider_calls

    @staticmethod
    def label_photos(photos: Sequence[Photograph]) -> dict[str, Photograph]:
        ordered = sorted(photos, key=lambda photo: (photo.original_filename, photo.id))
        return {f"P{index:02d}": photo for index, photo in enumerate(ordered, start=1)}

    def analyzed_photos(self, project_id: str) -> list[Photograph]:
        return [
            photo
            for photo in self.repository.list_photos(project_id)
            if photo.state is ProcessingState.COMPLETED
            and (feature := self.repository.get_feature(photo.id)) is not None
            and feature.model_fingerprint == self.encoder.fingerprint
        ]

    def is_current(self, project_id: str) -> bool:
        project = self.repository.get(project_id)
        latest = self.repository.latest_interpretation(project_id)
        return bool(
            project
            and project.brief
            and latest
            and latest.status == "completed"
            and latest.prompt_hash == prompt_hash(project.brief.original_text)
        )

    def run(self, project_id: str) -> BriefInterpretation:
        project = self.repository.get(project_id)
        if project is None or project.brief is None:
            raise ValueError("A saved creative brief is required for interpretation.")
        brief = project.brief.original_text
        record = {
            "id": str(uuid4()),
            "project_id": project_id,
            "prompt_hash": prompt_hash(brief),
            "provider": self.reasoner.provider,
            "model_name": self.reasoner.model_name,
        }

        def fail(code: str, message: str, called: bool, **extra) -> BriefInterpretation:
            interpretation = BriefInterpretation(
                **record,
                status="failed",
                provider_called=called,
                error_code=code,
                error_message=message,
                **extra,
            )
            self.repository.save_interpretation(interpretation, [])
            return interpretation

        if self.repository.provider_call_count(project_id) >= self.max_provider_calls:
            return fail(
                "request_limit_reached",
                f"This project already used its {self.max_provider_calls} model requests.",
                called=False,
            )
        labeled = self.label_photos(self.analyzed_photos(project_id))
        if not labeled:
            return fail("no_analyzed_photos", "No analyzed photographs are available.", False)
        relevance = {
            photo.id: feature.brief_relevance
            for photo in labeled.values()
            if (feature := self.repository.get_feature(photo.id)) is not None
        }
        try:
            sheets = build_contact_sheets([(label, p.working_path) for label, p in labeled.items()])
        except (ContactSheetError, OSError) as error:
            return fail("contact_sheet_failed", str(error), called=False)

        request = ReasonerRequest(
            brief=brief,
            target=project.target_count or len(labeled),
            photos=tuple((label, relevance.get(photo.id)) for label, photo in labeled.items()),
            contact_sheets=tuple(sheets),
        )
        started = time.monotonic()
        try:
            response = self.reasoner.interpret(request)
        except ReasonerError as error:
            return fail(error.code, str(error), called=True, duration_ms=_elapsed(started))
        except Exception as error:  # noqa: BLE001 - never let a provider bug look like success
            return fail("provider_error", str(error) or "The model call failed.", True,
                        duration_ms=_elapsed(started))
        usage = {
            "duration_ms": _elapsed(started),
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "raw_response": response.content,
        }
        try:
            parsed = parse_interpretation(
                response.content, {label: photo.id for label, photo in labeled.items()}
            )
            scores = self._score(labeled.values(), parsed, relevance)
        except InterpretationError as error:
            return fail(error.code, str(error), called=True, **usage)
        except Exception as error:  # noqa: BLE001 - descriptor encoding or cache failure
            return fail("scoring_failed", str(error) or "Guided scoring failed.", True, **usage)

        interpretation = BriefInterpretation(
            **record,
            status="completed",
            provider_called=True,
            summary=parsed.summary,
            positive_descriptors=parsed.positive_descriptors,
            negative_descriptors=parsed.negative_descriptors,
            photo_notes=parsed.photo_notes,
            **usage,
        )
        self.repository.save_interpretation(interpretation, scores)
        return interpretation

    def ranking(self, project_id: str) -> Ranking:
        latest = self.repository.latest_interpretation(project_id)
        if latest is not None and self.is_current(project_id):
            scores = self.repository.guided_scores(latest.id)
            return Ranking(
                "guided",
                tuple(
                    RankingEntry(s.photo_id, rank, s.guided_score, s.brief_relevance, s.explanation)
                    for rank, s in enumerate(scores, start=1)
                ),
            )
        relevance = [
            (photo.id, feature.brief_relevance)
            for photo in self.analyzed_photos(project_id)
            if (feature := self.repository.get_feature(photo.id)) is not None
            and feature.brief_relevance is not None
        ]
        relevance.sort(key=lambda item: (-item[1], item[0]))
        return Ranking(
            "brief_relevance",
            tuple(
                RankingEntry(photo_id, rank, None, score, None)
                for rank, (photo_id, score) in enumerate(relevance, start=1)
            ),
        )

    def _score(
        self,
        photos,
        parsed: ParsedInterpretation,
        relevance: Mapping[str, float | None],
    ) -> list[GuidedScore]:
        image_vectors = {}
        for photo in photos:
            feature = self.repository.get_feature(photo.id)
            vector = self.cache.load(feature.embedding_path, feature.embedding_dimension)
            if vector is None:
                raise InterpretationError(
                    "scoring_failed", f"Cached embedding for {photo.original_filename} is missing."
                )
            image_vectors[photo.id] = vector
        return compute_guided_scores(
            image_vectors,
            [(text, self._text_vector(text)) for text in parsed.positive_descriptors],
            [(text, self._text_vector(text)) for text in parsed.negative_descriptors],
            parsed.photo_notes,
            relevance,
        )

    def _text_vector(self, text: str) -> np.ndarray:
        path = self.cache.prompt_path(self.encoder.fingerprint, prompt_hash(text))
        vector = self.cache.load(path, self.encoder.dimension)
        if vector is None:
            vector = self.cache.save(path, self.encoder.encode_text(text))
        return vector


def _elapsed(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
