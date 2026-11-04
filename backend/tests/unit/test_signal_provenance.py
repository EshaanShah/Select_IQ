import pytest

from selectiq.domain.models import SignalProvenance


def provenance(**overrides) -> SignalProvenance:
    values = {
        "embedding_model": "ViT-B-32 / laion2b_s34b_b79k",
        "embeddings_genuine": True,
        "guidance_model": "groq / qwen/qwen3.8-27b",
        "guidance_status": "completed",
        "guidance_genuine": True,
        "comparisons_used": 5,
        "preference_method": "regularized_pairwise_logistic",
        "excluded_photo_count": 0,
    }
    return SignalProvenance(**{**values, **overrides})


def test_real_clip_and_completed_groq_guidance_is_ai_informed() -> None:
    result = provenance()
    assert result.kind == "ai_informed"
    assert result.is_genuine_ai is True
    assert "AI-informed" in result.label
    assert "ViT-B-32" in result.label and "qwen" in result.label and "5 saved choices" in result.label


@pytest.mark.parametrize("status", ["failed", "not_started"])
def test_real_clip_without_completed_guidance_is_partial(status: str) -> None:
    result = provenance(guidance_status=status, guidance_genuine=False)
    assert result.kind == "partial_ai"
    assert result.is_genuine_ai is False
    assert "AI interpretation unavailable" in result.label
    assert "basic relevance" in result.label


def test_offline_reasoner_with_real_clip_is_partial_and_says_so() -> None:
    result = provenance(guidance_model="scripted / scripted-test", guidance_genuine=False)
    assert result.kind == "partial_ai"
    assert "offline stand-in" in result.label


def test_test_encoder_is_never_presented_as_ai() -> None:
    result = provenance(embedding_model="deterministic-test / v1", embeddings_genuine=False)
    assert result.kind == "test_signals"
    assert result.is_genuine_ai is False
    assert result.label.startswith("Test signals (not AI)")


def test_label_reports_zero_and_one_choice_honestly() -> None:
    assert "no saved choices" in provenance(comparisons_used=0).label
    assert "1 saved choice" in provenance(comparisons_used=1).label
