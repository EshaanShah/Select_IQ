"""A-06 red tests for the project-specific pairwise preference model.

The model is a regularized pairwise logistic (Bradley-Terry style) ranker over
photo feature vectors: P(A over B) = sigmoid(w . (x_A - x_B)). These tests use
small synthetic features so a "known preference" is unambiguous.
"""

import math

import numpy as np
import pytest

from selectiq.domain.models import ComparisonChoice
from selectiq.intelligence.preference_model import (
    PairwisePreferenceModel,
    PreferenceScores,
)

PROJECT = "project-1"


def choice(winner: str, loser: str, sequence: int = 1) -> ComparisonChoice:
    return ComparisonChoice(project_id=PROJECT, winner_id=winner, loser_id=loser, sequence=sequence)


def choices(*pairs: tuple[str, str]) -> list[ComparisonChoice]:
    return [choice(winner, loser, index + 1) for index, (winner, loser) in enumerate(pairs)]


# Feature 0 is the controlled "preferred" property (e.g. peak action);
# feature 1 is an unrelated nuisance property.
SYNTHETIC = {
    "high_a": np.array([1.0, 0.2]),
    "high_b": np.array([0.9, 0.8]),
    "low_a": np.array([0.1, 0.3]),
    "low_b": np.array([0.0, 0.9]),
    "unseen_high": np.array([0.95, 0.5]),
    "unseen_low": np.array([0.05, 0.5]),
}


def fit(features=SYNTHETIC, observations=(), **kwargs) -> PreferenceScores:
    return PairwisePreferenceModel(**kwargs).fit(features, list(observations))


def test_zero_choices_produce_neutral_scores_for_every_photo() -> None:
    result = fit()

    assert set(result.scores) == set(SYNTHETIC)
    assert all(score == pytest.approx(0.0) for score in result.scores.values())
    assert result.comparisons_used == 0


def test_known_preference_generalizes_to_unseen_photos() -> None:
    result = fit(observations=choices(("high_a", "low_a"), ("high_b", "low_b"), ("high_a", "low_b")))

    assert result.scores["unseen_high"] > result.scores["unseen_low"]
    assert result.scores["high_a"] > result.scores["low_a"]
    assert result.scores["high_b"] > result.scores["low_b"]


def test_single_choice_raises_winner_relative_to_loser() -> None:
    before = fit()
    after = fit(observations=choices(("low_a", "high_a")))

    before_gap = before.scores["low_a"] - before.scores["high_a"]
    after_gap = after.scores["low_a"] - after.scores["high_a"]
    assert after_gap > before_gap
    assert after.scores["low_a"] > after.scores["high_a"]
    assert after.comparisons_used == 1


def test_more_consistent_evidence_strengthens_the_preference() -> None:
    one = fit(observations=choices(("high_a", "low_a")))
    three = fit(observations=choices(("high_a", "low_a"), ("high_b", "low_b"), ("high_a", "low_b")))

    gap_one = one.scores["unseen_high"] - one.scores["unseen_low"]
    gap_three = three.scores["unseen_high"] - three.scores["unseen_low"]
    assert gap_three > gap_one > 0


def test_conflicting_choices_cancel_rather_than_compound() -> None:
    consistent = fit(observations=choices(("high_a", "low_a"), ("high_b", "low_b")))
    conflicting = fit(observations=choices(("high_a", "low_a"), ("low_b", "high_b")))

    consistent_gap = consistent.scores["unseen_high"] - consistent.scores["unseen_low"]
    conflicting_gap = conflicting.scores["unseen_high"] - conflicting.scores["unseen_low"]
    assert abs(conflicting_gap) < consistent_gap
    for score in conflicting.scores.values():
        assert math.isfinite(score)


def test_exactly_opposed_choices_on_mirrored_features_are_neutral() -> None:
    features = {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0])}

    result = fit(features, choices(("a", "b"), ("b", "a")))

    assert result.scores["a"] == pytest.approx(result.scores["b"], abs=1e-6)


def test_pair_order_does_not_bias_the_result() -> None:
    forward = fit(observations=choices(("high_a", "low_a"), ("high_b", "low_b")))
    reversed_order = fit(observations=choices(("high_b", "low_b"), ("high_a", "low_a")))

    for photo_id in SYNTHETIC:
        assert forward.scores[photo_id] == pytest.approx(reversed_order.scores[photo_id], abs=1e-9)


def test_feature_permutation_of_input_mapping_does_not_change_scores() -> None:
    shuffled = dict(reversed(list(SYNTHETIC.items())))
    observations = choices(("high_a", "low_a"))

    assert fit(observations=observations).scores == pytest.approx(
        fit(shuffled, observations).scores
    )


def test_results_are_reproducible_with_a_fixed_seed() -> None:
    observations = choices(("high_a", "low_a"), ("low_b", "high_b"), ("unseen_high", "low_a"))

    first = fit(observations=observations, seed=7)
    second = fit(observations=observations, seed=7)

    assert first.scores == second.scores
    assert np.array_equal(first.weights, second.weights)


def test_regularization_keeps_scores_bounded_with_few_choices() -> None:
    result = fit(observations=choices(("high_a", "low_a")))

    assert all(abs(score) < 10.0 for score in result.scores.values())
    assert np.all(np.isfinite(result.weights))


def test_stronger_regularization_shrinks_toward_neutral() -> None:
    observations = choices(("high_a", "low_a"), ("high_b", "low_b"))

    weak = fit(observations=observations, regularization=0.1)
    strong = fit(observations=observations, regularization=100.0)

    assert np.linalg.norm(strong.weights) < np.linalg.norm(weak.weights)


def test_scores_are_relative_within_the_project() -> None:
    result = fit(observations=choices(("high_a", "low_a")))

    assert sum(result.scores.values()) / len(result.scores) == pytest.approx(0.0, abs=1e-9)


def test_unknown_photo_in_a_choice_is_rejected() -> None:
    with pytest.raises(ValueError):
        fit(observations=choices(("high_a", "not-a-photo")))


def test_choice_comparing_a_photo_with_itself_is_rejected() -> None:
    with pytest.raises(ValueError):
        fit(observations=choices(("high_a", "high_a")))


def test_mismatched_feature_dimensions_are_rejected() -> None:
    features = {"a": np.array([1.0, 0.0]), "b": np.array([1.0, 0.0, 0.5])}

    with pytest.raises(ValueError):
        fit(features)


def test_non_finite_features_are_rejected() -> None:
    features = {"a": np.array([1.0, np.nan]), "b": np.array([0.0, 1.0])}

    with pytest.raises(ValueError):
        fit(features)


def test_output_is_honestly_labeled_as_a_simple_pairwise_ranker() -> None:
    result = fit(observations=choices(("high_a", "low_a")))

    assert result.model_version
    assert result.method == "regularized_pairwise_logistic"
    assert "active" not in result.method.lower()
