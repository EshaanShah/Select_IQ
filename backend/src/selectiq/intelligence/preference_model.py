"""Learn project-specific preference evidence from A/B choices."""

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression

from selectiq.domain.models import ComparisonChoice


@dataclass(frozen=True, slots=True)
class PreferenceScores:
    scores: dict[str, float]
    weights: np.ndarray
    comparisons_used: int
    method: str = "regularized_pairwise_logistic"
    model_version: str = "pairwise-logistic-v1"


class PairwisePreferenceModel:
    """Regularized linear ranker trained on winner-minus-loser embeddings."""

    method = "regularized_pairwise_logistic"
    model_version = "pairwise-logistic-v1"

    def __init__(self, regularization: float = 1.0, seed: int = 0) -> None:
        if not np.isfinite(regularization) or regularization <= 0:
            raise ValueError("Regularization must be a positive finite number.")
        self.regularization = float(regularization)
        self.seed = seed

    def fit(
        self,
        features: dict[str, np.ndarray],
        choices: list[ComparisonChoice],
    ) -> PreferenceScores:
        vectors, dimension = self._validated_features(features)
        if not choices:
            return self._result(vectors, np.zeros(dimension), 0)

        differences: list[np.ndarray] = []
        for choice in choices:
            if choice.winner_id == choice.loser_id:
                raise ValueError("A preference choice requires two distinct photos.")
            if choice.winner_id not in vectors or choice.loser_id not in vectors:
                raise ValueError("Every preference choice must reference a known photo.")
            differences.append(vectors[choice.winner_id] - vectors[choice.loser_id])

        positive = np.stack(differences)
        training_features = np.concatenate((positive, -positive), axis=0)
        labels = np.concatenate(
            (np.ones(len(positive), dtype=np.int8), np.zeros(len(positive), dtype=np.int8))
        )
        estimator = LogisticRegression(
            C=1.0 / self.regularization,
            fit_intercept=False,
            solver="lbfgs",
            max_iter=1000,
            tol=1e-12,
            random_state=self.seed,
        )
        estimator.fit(training_features, labels)
        weights = np.asarray(estimator.coef_[0], dtype=np.float64)
        return self._result(vectors, weights, len(choices))

    @staticmethod
    def _validated_features(
        features: dict[str, np.ndarray],
    ) -> tuple[dict[str, np.ndarray], int]:
        if not features:
            raise ValueError("At least one photo feature is required.")
        vectors: dict[str, np.ndarray] = {}
        dimension: int | None = None
        for photo_id, value in features.items():
            vector = np.asarray(value, dtype=np.float64)
            if vector.ndim != 1 or vector.size == 0:
                raise ValueError("Photo features must be nonempty one-dimensional vectors.")
            if not np.isfinite(vector).all():
                raise ValueError("Photo features must contain only finite values.")
            if dimension is None:
                dimension = int(vector.size)
            elif vector.size != dimension:
                raise ValueError("All photo features must have the same dimension.")
            vectors[photo_id] = vector
        assert dimension is not None
        return vectors, dimension

    def _result(
        self, vectors: dict[str, np.ndarray], weights: np.ndarray, comparisons_used: int
    ) -> PreferenceScores:
        raw = {photo_id: float(vector @ weights) for photo_id, vector in vectors.items()}
        mean = sum(raw.values()) / len(raw)
        scores = {photo_id: score - mean for photo_id, score in raw.items()}
        return PreferenceScores(
            scores=scores,
            weights=weights,
            comparisons_used=comparisons_used,
            method=self.method,
            model_version=self.model_version,
        )

