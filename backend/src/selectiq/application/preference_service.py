"""Project-scoped preference scoring over cached A-03 image embeddings."""

import numpy as np

from selectiq.domain.errors import ProjectNotFoundError, ValidationError
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.project_repository import ProjectRepository
from selectiq.intelligence.preference_model import PairwisePreferenceModel, PreferenceScores


class PreferenceService:
    def __init__(
        self,
        repository: ProjectRepository,
        embedding_cache: NumpyEmbeddingCache,
        model: PairwisePreferenceModel,
    ) -> None:
        self.repository = repository
        self.embedding_cache = embedding_cache
        self.model = model

    def scores(self, project_id: str) -> PreferenceScores:
        project = self.repository.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")

        features: dict[str, np.ndarray] = {}
        for photo in project.photos:
            feature = self.repository.get_feature(photo.id)
            if feature is None:
                continue
            vector = self.embedding_cache.load(
                feature.embedding_path, feature.embedding_dimension
            )
            if vector is not None:
                features[photo.id] = vector
        if not features:
            raise ValidationError("Complete image analysis before calculating preferences.")

        usable_choices = [
            choice
            for choice in self.repository.comparison_choices(project_id)
            if choice.winner_id in features and choice.loser_id in features
        ]
        return self.model.fit(features, usable_choices)
