"""Provider-independent image/text feature extraction for Alpha story A-03."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from selectiq.domain.models import PhotoFeature, Photograph
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache, validate_embedding
from selectiq.infrastructure.model_adapters import ModelLoadError, VisualEncoder
from selectiq.infrastructure.project_repository import ProjectRepository


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    completed: tuple[str, ...]
    failed: tuple[str, ...]


class FeatureExtractor:
    def __init__(
        self,
        repository: ProjectRepository,
        cache: NumpyEmbeddingCache,
        encoder: VisualEncoder,
        batch_size: int = 8,
    ) -> None:
        self.repository = repository
        self.cache = cache
        self.encoder = encoder
        self.batch_size = batch_size

    def analyze(self, photos: list[Photograph]) -> AnalysisResult:
        completed: list[str] = []
        failed: list[str] = []
        misses: list[Photograph] = []

        for photo in photos:
            feature = self.repository.get_feature(photo.id)
            path = self.cache.image_path(self.encoder.fingerprint, photo.content_hash)
            expected = feature.embedding_dimension if feature else self.encoder.dimension
            cached = self.cache.load(path, expected)
            if cached is None or (feature and feature.model_fingerprint != self.encoder.fingerprint):
                misses.append(photo)
                continue
            self.repository.save_feature(self._feature(photo, path, cached.size, feature))
            completed.append(photo.id)

        for offset in range(0, len(misses), self.batch_size):
            batch = misses[offset : offset + self.batch_size]
            for photo in batch:
                self.repository.mark_photo_processing(photo.id)
            try:
                vectors = self._validate_batch(self.encoder.encode_images([p.working_path for p in batch]), len(batch))
            except ModelLoadError as error:
                unresolved = misses[offset:]
                for photo in unresolved:
                    self._fail(photo, error, code="model_load_failed")
                    failed.append(photo.id)
                break
            except Exception:  # noqa: BLE001 - isolate arbitrary provider/decoder failures
                # Retry individually so one unreadable photograph cannot hide successful inference.
                for photo in batch:
                    try:
                        vector = self._validate_batch(
                            self.encoder.encode_images([photo.working_path]), 1
                        )[0]
                        self._persist(photo, vector)
                        completed.append(photo.id)
                    except Exception as error:  # noqa: BLE001 - persist provider failure safely
                        self._fail(photo, error)
                        failed.append(photo.id)
                continue
            for photo, vector in zip(batch, vectors, strict=True):
                try:
                    self._persist(photo, vector)
                    completed.append(photo.id)
                except Exception as error:  # noqa: BLE001 - one artifact must not abort the gallery
                    self._fail(photo, error)
                    failed.append(photo.id)

        return AnalysisResult(tuple(completed), tuple(failed))

    def score_prompt(self, project_id: str, prompt: str) -> dict[str, float]:
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        prompt_path = self.cache.prompt_path(self.encoder.fingerprint, prompt_hash)
        prompt_vector = self.cache.load(prompt_path, self.encoder.dimension)
        if prompt_vector is None:
            prompt_vector = self.cache.save(prompt_path, self.encoder.encode_text(prompt))

        scores: dict[str, float] = {}
        for photo in self.repository.list_photos(project_id):
            feature = self.repository.get_feature(photo.id)
            if feature is None or feature.model_fingerprint != self.encoder.fingerprint:
                continue
            image_vector = self.cache.load(feature.embedding_path, prompt_vector.size)
            if image_vector is None:
                continue
            score = float(image_vector @ prompt_vector)
            self.repository.update_relevance(photo.id, prompt_hash, score)
            scores[photo.id] = score
        return scores

    def is_current(self, photo: Photograph) -> bool:
        feature = self.repository.get_feature(photo.id)
        if feature is None or feature.model_fingerprint != self.encoder.fingerprint:
            return False
        return self.cache.load(feature.embedding_path, feature.embedding_dimension) is not None

    def _validate_batch(self, values: np.ndarray, count: int) -> np.ndarray:
        matrix = np.asarray(values, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != count or matrix.shape[1] == 0:
            raise ValueError("Encoder returned an invalid image embedding matrix.")
        vectors = np.stack([validate_embedding(row) for row in matrix])
        dimensions = {row.size for row in vectors}
        if len(dimensions) != 1:
            raise ValueError("Encoder returned inconsistent embedding dimensions.")
        self.encoder.dimension = int(vectors.shape[1])
        return vectors

    def _persist(self, photo: Photograph, vector: np.ndarray) -> None:
        path = self.cache.image_path(self.encoder.fingerprint, photo.content_hash)
        saved = self.cache.save(path, vector)
        previous = self.repository.get_feature(photo.id)
        self.repository.save_feature(self._feature(photo, path, saved.size, previous))

    def _feature(
        self,
        photo: Photograph,
        path: Path,
        dimension: int,
        previous: PhotoFeature | None,
    ) -> PhotoFeature:
        compatible_previous = (
            previous if previous and previous.model_fingerprint == self.encoder.fingerprint else None
        )
        return PhotoFeature(
            photo_id=photo.id,
            model_name=self.encoder.model_name,
            checkpoint=self.encoder.checkpoint,
            model_fingerprint=self.encoder.fingerprint,
            embedding_dimension=dimension,
            embedding_path=path,
            prompt_hash=compatible_previous.prompt_hash if compatible_previous else None,
            brief_relevance=(
                compatible_previous.brief_relevance if compatible_previous else None
            ),
        )

    def _fail(self, photo: Photograph, error: Exception, code: str = "inference_failed") -> None:
        self.repository.mark_photo_failed(photo.id, code, str(error) or "Inference failed.")

