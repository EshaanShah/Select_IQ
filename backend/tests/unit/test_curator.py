import math
import random

import pytest

from selectiq.domain.errors import ValidationError
from selectiq.intelligence.curator import (
    PhotoSignals,
    SignalWeights,
    evidence_weighted,
    propose,
)


def gallery(count: int) -> list[PhotoSignals]:
    return [
        PhotoSignals(
            photo_id=f"photo-{index:02d}",
            prompt_relevance=(index * 7 % count) / count,
            ai_guidance=(index * 11 % count) / count,
            preference=(index * 13 % count) / count,
        )
        for index in range(count)
    ]


def selected_ids(signals: list[PhotoSignals], target: int, **kwargs) -> list[str]:
    return [item.photo_id for item in propose(signals, target, **kwargs)]


def test_typical_demo_selects_exactly_five_distinct_allowed_photos_from_eighteen() -> None:
    signals = gallery(18)
    proposal = propose(signals, 5)
    ids = [item.photo_id for item in proposal]
    assert len(ids) == 5
    assert len(set(ids)) == 5
    assert set(ids) <= {signal.photo_id for signal in signals}
    assert [item.rank for item in proposal] == [1, 2, 3, 4, 5]


@pytest.mark.parametrize("target", [1, 18])
def test_targets_of_one_and_all_photos_are_supported(target: int) -> None:
    signals = gallery(18)
    ids = selected_ids(signals, target)
    assert len(ids) == len(set(ids)) == target


@pytest.mark.parametrize("target", [0, -1, 19])
def test_rejects_targets_outside_one_through_gallery_size(target: int) -> None:
    with pytest.raises(ValidationError, match="between 1 and 18"):
        propose(gallery(18), target)


def test_rejects_an_empty_gallery() -> None:
    with pytest.raises(ValidationError, match="no photographs"):
        propose([], 1)


def test_rejects_duplicate_photo_ids() -> None:
    duplicate = [PhotoSignals("same", 0.1, 0.1, 0.1), PhotoSignals("same", 0.9, 0.9, 0.9)]
    with pytest.raises(ValidationError, match="unique"):
        propose(duplicate, 1)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_rejects_non_finite_signals(bad: float) -> None:
    signals = [PhotoSignals("a", bad, 0.1, 0.1), PhotoSignals("b", 0.2, 0.2, 0.2)]
    with pytest.raises(ValidationError, match="finite"):
        propose(signals, 1)


def test_results_are_deterministic_and_independent_of_input_order() -> None:
    signals = gallery(18)
    shuffled = signals[:]
    random.Random(7).shuffle(shuffled)
    assert propose(signals, 5) == propose(signals, 5) == propose(shuffled, 5)


def test_exact_ties_are_broken_by_photo_id() -> None:
    signals = [PhotoSignals(photo_id, 0.5, 0.5, 0.5) for photo_id in ("c", "a", "b")]
    assert selected_ids(signals, 2) == ["a", "b"]


@pytest.mark.parametrize("component", ["prompt_relevance", "ai_guidance", "preference"])
def test_each_signal_independently_changes_the_ranking(component: str) -> None:
    neutral = {"prompt_relevance": 0.5, "ai_guidance": 0.5, "preference": 0.5}
    low = PhotoSignals("a-low", **neutral)
    high = PhotoSignals("b-high", **neutral)
    assert selected_ids([low, high], 1) == ["a-low"]

    boosted = PhotoSignals("b-high", **{**neutral, component: 0.9})
    assert selected_ids([low, boosted], 1) == ["b-high"]


def test_weights_control_which_signal_dominates() -> None:
    prompt_favorite = PhotoSignals("prompt", prompt_relevance=1.0, ai_guidance=0.0, preference=0.0)
    choice_favorite = PhotoSignals("choice", prompt_relevance=0.0, ai_guidance=0.0, preference=1.0)
    signals = [prompt_favorite, choice_favorite]
    prompt_heavy = SignalWeights(prompt_relevance=2.0, ai_guidance=1.0, preference=1.0)
    choice_heavy = SignalWeights(prompt_relevance=1.0, ai_guidance=1.0, preference=2.0)
    assert selected_ids(signals, 1, weights=prompt_heavy) == ["prompt"]
    assert selected_ids(signals, 1, weights=choice_heavy) == ["choice"]


def test_rejects_negative_or_all_zero_weights() -> None:
    with pytest.raises(ValidationError, match="weight"):
        SignalWeights(prompt_relevance=-1.0)
    with pytest.raises(ValidationError, match="weight"):
        SignalWeights(prompt_relevance=0.0, ai_guidance=0.0, preference=0.0)


@pytest.mark.regression
def test_photo_that_lost_every_comparison_remains_eligible() -> None:
    loser = PhotoSignals("loser", prompt_relevance=1.0, ai_guidance=1.0, preference=0.0)
    winners = [
        PhotoSignals(f"winner-{index}", prompt_relevance=0.1, ai_guidance=0.1, preference=1.0)
        for index in range(4)
    ]
    assert "loser" in selected_ids([loser, *winners], 1)


def test_missing_signals_contribute_nothing_instead_of_failing() -> None:
    signals = [
        PhotoSignals("a", prompt_relevance=None, ai_guidance=None, preference=None),
        PhotoSignals("b", prompt_relevance=0.9, ai_guidance=None, preference=None),
        PhotoSignals("c", prompt_relevance=0.1, ai_guidance=None, preference=None),
    ]
    proposal = propose(signals, 3)
    assert [item.photo_id for item in proposal] == ["b", "a", "c"]
    assert proposal[1].score == proposal[2].score == 0.0


def test_uninformative_constant_signal_does_not_affect_ranking() -> None:
    signals = [
        PhotoSignals("a", prompt_relevance=0.3, ai_guidance=0.7, preference=0.2),
        PhotoSignals("b", prompt_relevance=0.3, ai_guidance=0.7, preference=0.8),
    ]
    proposal = propose(signals, 2)
    assert [item.photo_id for item in proposal] == ["b", "a"]
    assert all(item.contributions["prompt_relevance"] == 0.0 for item in proposal)
    assert all(item.contributions["ai_guidance"] == 0.0 for item in proposal)


def test_contributions_explain_the_score() -> None:
    proposal = propose(gallery(18), 5)
    for item in proposal:
        assert item.score == pytest.approx(sum(item.contributions.values()))
        assert set(item.contributions) == {"prompt_relevance", "ai_guidance", "preference"}


@pytest.mark.parametrize(
    ("choices", "expected"), [(0, 0.0), (5, 1.0), (10, 4 / 3), (1000, 2.0)]
)
def test_preference_weight_grows_with_saved_choices(choices: int, expected: float) -> None:
    weights = evidence_weighted(choices)
    assert weights.prompt_relevance == 1.0
    assert weights.ai_guidance == 1.0
    assert weights.preference == pytest.approx(expected, abs=0.01)


def test_negative_choice_counts_are_rejected() -> None:
    with pytest.raises(ValidationError, match="choices"):
        evidence_weighted(-1)


def test_zero_choices_leave_ranking_to_prompt_and_guidance() -> None:
    by_preference = PhotoSignals("pref", prompt_relevance=0.0, ai_guidance=0.0, preference=1.0)
    by_prompt = PhotoSignals("prompt", prompt_relevance=1.0, ai_guidance=0.0, preference=0.0)
    assert selected_ids([by_preference, by_prompt], 1, weights=evidence_weighted(0)) == ["prompt"]
