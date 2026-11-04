import os

import pytest
from PIL import Image, ImageDraw

from selectiq.infrastructure.contact_sheet import build_contact_sheets
from selectiq.infrastructure.reasoners import GroqBriefReasoner, ReasonerRequest
from selectiq.intelligence.brief_interpreter import parse_interpretation


@pytest.mark.real_llm
def test_groq_returns_a_valid_grounded_interpretation(tmp_path) -> None:
    if os.getenv("SELECTIQ_RUN_REAL_LLM_TESTS") != "1":
        pytest.skip("Set SELECTIQ_RUN_REAL_LLM_TESTS=1 and GROQ_API_KEY to call Groq")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY is not set")

    bright = tmp_path / "bright.jpg"
    image = Image.new("RGB", (480, 360), "#f6d77a")
    draw = ImageDraw.Draw(image)
    draw.ellipse((160, 60, 320, 220), fill="#f0c090", outline="#4a3020", width=6)
    draw.arc((200, 120, 280, 190), start=20, end=160, fill="#4a3020", width=8)
    image.save(bright, "JPEG")
    dark = tmp_path / "dark.jpg"
    Image.new("RGB", (480, 360), "#101418").save(dark, "JPEG")
    labels = {"P01": "bright", "P02": "dark"}

    reasoner = GroqBriefReasoner(
        api_key=api_key,
        model=os.getenv("SELECTIQ_GROQ_MODEL", "qwen/qwen3.8-27b"),
        timeout_seconds=60,
    )
    response = reasoner.interpret(
        ReasonerRequest(
            brief="Only well lit photos with a smiling face.",
            target=1,
            photos=(("P01", 0.24), ("P02", 0.11)),
            contact_sheets=tuple(build_contact_sheets([("P01", bright), ("P02", dark)])),
        )
    )
    parsed = parse_interpretation(response.content, labels)

    assert parsed.summary
    assert parsed.positive_descriptors
    assert {note.photo_id for note in parsed.photo_notes} <= set(labels.values())
