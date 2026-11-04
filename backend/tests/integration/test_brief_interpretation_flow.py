import json
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from selectiq.application.project_service import PhotoUpload
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.reasoners import ReasonerError, ScriptedBriefReasoner
from selectiq.intelligence.brief_interpreter import BriefInterpreter
from selectiq.intelligence.feature_extractor import FeatureExtractor

AXES = {"red": 0, "green": 1, "blue": 2}
TEXT = {
    "Bright warm scenes.": (1.0, 0.2, 0.0),
    "a person smiling": (0.1, 1.0, 0.0),
    "a dark underexposed photo": (0.0, 0.0, 1.0),
}


class ColorAxisEncoder:
    """Controlled encoder: each solid-colour photo owns one axis of a 3-d space."""

    model_name = "color-axis-test"
    checkpoint = "v1"
    fingerprint = "color-axis-test-v1"
    dimension = 3

    def encode_images(self, image_paths: Sequence[Path]) -> np.ndarray:
        vectors = []
        for path in image_paths:
            with Image.open(path) as image:
                pixel = image.convert("RGB").getpixel((0, 0))
            vector = np.zeros(3, dtype=np.float32)
            vector[int(np.argmax(pixel))] = 1.0
            vectors.append(vector)
        return np.stack(vectors)

    def encode_text(self, text: str) -> np.ndarray:
        vector = np.asarray(TEXT[text], dtype=np.float32)
        return vector / np.linalg.norm(vector)


def jpeg(color: str) -> bytes:
    output = BytesIO()
    Image.new("RGB", (64, 48), color).save(output, format="JPEG")
    return output.getvalue()


def response(notes=None, **overrides) -> str:
    body = {
        "summary": "Favor genuine smiles over warm colour alone.",
        "positive_descriptors": ["a person smiling"],
        "negative_descriptors": ["a dark underexposed photo"],
        "photo_notes": notes or [],
    }
    body.update(overrides)
    return json.dumps(body)


@pytest.fixture
def analyzed(project_service, tmp_path):
    project = project_service.create_project()
    photos = project_service.import_photos(
        project.id,
        [PhotoUpload(f"{name}.jpg", BytesIO(jpeg(name))) for name in ("red", "green", "blue")],
    ).accepted
    project_service.set_prompt_and_target(project.id, "Bright warm scenes.", 2)
    encoder = ColorAxisEncoder()
    cache = NumpyEmbeddingCache(tmp_path / "cache")
    extractor = FeatureExtractor(project_service.repository, cache, encoder)
    extractor.analyze(photos)
    extractor.score_prompt(project.id, "Bright warm scenes.")
    by_name = {photo.original_filename: photo.id for photo in photos}
    return project.id, by_name, cache, encoder


def interpreter_for(project_service, analyzed, reasoner, max_calls: int = 5) -> BriefInterpreter:
    _, _, cache, encoder = analyzed
    return BriefInterpreter(
        project_service.repository, cache, encoder, reasoner, max_provider_calls=max_calls
    )


def test_completed_interpretation_is_grounded_persisted_and_changes_ranking(
    project_service, analyzed
) -> None:
    project_id, ids, _, _ = analyzed
    reasoner = ScriptedBriefReasoner([response()])
    interpreter = interpreter_for(project_service, analyzed, reasoner)

    before = interpreter.ranking(project_id)
    assert before.basis == "brief_relevance"
    assert before.entries[0].photo_id == ids["red.jpg"]

    result = interpreter.run(project_id)

    assert result.status == "completed"
    assert result.provider == "scripted" and result.provider_called is True
    request = reasoner.requests[0]
    assert request.brief == "Bright warm scenes." and request.target == 2
    assert [label for label, _ in request.photos] == ["P01", "P02", "P03"]
    assert len(request.contact_sheets) == 1

    stored = project_service.repository.latest_interpretation(project_id)
    assert stored is not None and stored.id == result.id
    assert stored.positive_descriptors == ("a person smiling",)
    assert stored.raw_response == response()
    assert interpreter.is_current(project_id)

    after = interpreter.ranking(project_id)
    assert after.basis == "guided"
    assert after.entries[0].photo_id == ids["green.jpg"]
    assert after.entries[-1].photo_id == ids["blue.jpg"]
    assert all(entry.explanation for entry in after.entries)


def test_photo_notes_use_real_ids_and_adjust_scores(project_service, analyzed) -> None:
    project_id, ids, _, _ = analyzed
    labels = {photo.id: label for label, photo in BriefInterpreter.label_photos(
        project_service.repository.list_photos(project_id)
    ).items()}
    note = {"label": labels[ids["blue.jpg"]], "effect": "boost", "reason": "Decisive moment."}
    interpreter = interpreter_for(
        project_service, analyzed, ScriptedBriefReasoner([response(notes=[note])])
    )

    result = interpreter.run(project_id)

    assert result.photo_notes[0].photo_id == ids["blue.jpg"]
    scores = {score.photo_id: score for score in project_service.repository.guided_scores(result.id)}
    assert scores[ids["blue.jpg"]].note_adjustment > 0
    assert "Decisive moment." in scores[ids["blue.jpg"]].explanation


@pytest.mark.parametrize(
    ("scripted", "code"),
    [
        (ReasonerError("timeout", "Groq did not answer within 30 seconds."), "timeout"),
        ("this is not json", "malformed_output"),
        (
            response(notes=[{"label": "P77", "effect": "boost", "reason": "Invented."}]),
            "unknown_photo_id",
        ),
    ],
)
def test_failures_are_recorded_and_ranking_falls_back(
    project_service, analyzed, scripted, code
) -> None:
    project_id, ids, _, _ = analyzed
    interpreter = interpreter_for(project_service, analyzed, ScriptedBriefReasoner([scripted]))

    result = interpreter.run(project_id)

    assert result.status == "failed"
    assert result.error_code == code
    assert result.summary is None and result.positive_descriptors == ()
    assert project_service.repository.guided_scores(result.id) == []
    assert not interpreter.is_current(project_id)
    ranking = interpreter.ranking(project_id)
    assert ranking.basis == "brief_relevance"
    assert ranking.entries[0].photo_id == ids["red.jpg"]


def test_provider_call_limit_is_enforced(project_service, analyzed) -> None:
    project_id, _, _, _ = analyzed
    reasoner = ScriptedBriefReasoner([ReasonerError("rate_limited", "busy"), response()])
    interpreter = interpreter_for(project_service, analyzed, reasoner, max_calls=1)

    assert interpreter.run(project_id).error_code == "rate_limited"
    limited = interpreter.run(project_id)

    assert limited.status == "failed"
    assert limited.error_code == "request_limit_reached"
    assert limited.provider_called is False
    assert len(reasoner.requests) == 1


def test_changing_the_brief_makes_the_interpretation_stale(project_service, analyzed) -> None:
    project_id, _, _, _ = analyzed
    interpreter = interpreter_for(project_service, analyzed, ScriptedBriefReasoner([response()]))
    interpreter.run(project_id)
    assert interpreter.is_current(project_id)

    project_service.set_prompt_and_target(project_id, "Something else entirely.", 2)

    assert not interpreter.is_current(project_id)
