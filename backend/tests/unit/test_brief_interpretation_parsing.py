import json

import numpy as np
import pytest

from selectiq.domain.models import PhotoNote
from selectiq.intelligence.brief_interpreter import (
    InterpretationError,
    compute_guided_scores,
    parse_interpretation,
)

LABELS = {"P01": "photo-a", "P02": "photo-b", "P03": "photo-c"}


def payload(**overrides) -> str:
    body = {
        "summary": "Favor bright, joyful candid moments over posed portraits.",
        "positive_descriptors": ["a person smiling", "bright natural light"],
        "negative_descriptors": ["a dark underexposed photo"],
        "photo_notes": [{"label": "P02", "effect": "boost", "reason": "Wide genuine smile."}],
    }
    body.update(overrides)
    return json.dumps(body)


def test_valid_structured_response_maps_labels_to_photo_ids() -> None:
    parsed = parse_interpretation(payload(), LABELS)

    assert parsed.summary.startswith("Favor bright")
    assert parsed.positive_descriptors == ("a person smiling", "bright natural light")
    assert parsed.negative_descriptors == ("a dark underexposed photo",)
    assert parsed.photo_notes == (PhotoNote("photo-b", "boost", "Wide genuine smile."),)


def test_fenced_or_thinking_wrapped_json_is_accepted() -> None:
    raw = "<think>reasoning</think>\n```json\n" + payload() + "\n```"
    assert parse_interpretation(raw, LABELS).positive_descriptors[0] == "a person smiling"


@pytest.mark.parametrize("raw", ["", "not json", "[1, 2]", '{"summary": '])
def test_malformed_output_is_rejected(raw: str) -> None:
    with pytest.raises(InterpretationError) as error:
        parse_interpretation(raw, LABELS)
    assert error.value.code == "malformed_output"


@pytest.mark.parametrize(
    "overrides",
    [
        {"positive_descriptors": []},
        {"positive_descriptors": "smiling"},
        {"summary": ""},
        {"photo_notes": [{"label": "P01", "effect": "love", "reason": "x"}]},
        {"photo_notes": [{"label": "P01", "effect": "boost"}]},
        {
            "photo_notes": [
                {"label": "P01", "effect": "boost", "reason": "a"},
                {"label": "P01", "effect": "penalize", "reason": "b"},
            ]
        },
    ],
)
def test_schema_violations_are_rejected(overrides: dict) -> None:
    with pytest.raises(InterpretationError) as error:
        parse_interpretation(payload(**overrides), LABELS)
    assert error.value.code == "schema_violation"


def test_missing_field_is_a_schema_violation() -> None:
    body = json.loads(payload())
    del body["negative_descriptors"]
    with pytest.raises(InterpretationError) as error:
        parse_interpretation(json.dumps(body), LABELS)
    assert error.value.code == "schema_violation"


def test_invented_photo_id_rejects_the_whole_response() -> None:
    raw = payload(photo_notes=[{"label": "P09", "effect": "boost", "reason": "Not real."}])
    with pytest.raises(InterpretationError) as error:
        parse_interpretation(raw, LABELS)
    assert error.value.code == "unknown_photo_id"
    assert "P09" in str(error.value)


def test_descriptors_must_fit_the_clip_text_encoder() -> None:
    long_descriptor = " ".join(["word"] * 20)
    with pytest.raises(InterpretationError) as error:
        parse_interpretation(payload(positive_descriptors=[long_descriptor]), LABELS)
    assert error.value.code == "invalid_descriptor"


def test_duplicate_descriptors_are_collapsed() -> None:
    parsed = parse_interpretation(
        payload(positive_descriptors=["A person smiling", "a person smiling "]), LABELS
    )
    assert parsed.positive_descriptors == ("A person smiling",)


def unit(*values: float) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def test_model_guidance_changes_ranking_relative_to_brief_relevance() -> None:
    # photo-a matches the literal brief best, photo-b matches the model's descriptor.
    image_vectors = {"photo-a": unit(1, 0, 0), "photo-b": unit(0, 1, 0), "photo-c": unit(0, 0, 1)}
    brief_relevance = {"photo-a": 0.30, "photo-b": 0.10, "photo-c": 0.05}
    smiling = unit(0.1, 1, 0)
    dark = unit(0, 0, 1)

    scores = compute_guided_scores(
        image_vectors,
        positive=[("a person smiling", smiling)],
        negative=[("a dark underexposed photo", dark)],
        notes=[PhotoNote("photo-a", "penalize", "Eyes closed.")],
        brief_relevance=brief_relevance,
    )

    by_relevance = sorted(brief_relevance, key=brief_relevance.get, reverse=True)
    by_guidance = [score.photo_id for score in scores]
    assert by_relevance[0] == "photo-a"
    assert by_guidance[0] == "photo-b"
    assert by_guidance[-1] == "photo-c"
    top = scores[0]
    assert top.note_adjustment == 0.0
    assert top.guided_score == pytest.approx(top.descriptor_score)
    penalized = next(score for score in scores if score.photo_id == "photo-a")
    assert penalized.note_adjustment < 0
    assert "a person smiling" in top.explanation
    assert "Eyes closed." in penalized.explanation
    assert penalized.brief_relevance == 0.30
