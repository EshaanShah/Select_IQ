from io import BytesIO

import numpy as np

from selectiq.application.project_service import PhotoUpload
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.model_adapters import DeterministicVisualEncoder
from selectiq.intelligence.feature_extractor import FeatureExtractor


def test_embeddings_align_to_photo_ids_and_reanalysis_reuses_cache(
    project_service, jpeg_bytes, tmp_path
) -> None:
    project = project_service.create_project()
    imported = project_service.import_photos(
        project.id,
        [
            PhotoUpload("first.jpg", BytesIO(jpeg_bytes)),
            PhotoUpload("second.jpg", BytesIO(jpeg_bytes)),
        ],
    )
    encoder = DeterministicVisualEncoder(dimension=8)
    cache = NumpyEmbeddingCache(tmp_path / "cache")
    extractor = FeatureExtractor(project_service.repository, cache, encoder, batch_size=2)

    result = extractor.analyze(imported.accepted)
    assert set(result.completed) == {photo.id for photo in imported.accepted}
    assert result.failed == ()
    assert encoder.image_calls == 1

    for photo in imported.accepted:
        feature = project_service.repository.get_feature(photo.id)
        assert feature is not None
        vector = cache.load(feature.embedding_path, 8)
        assert vector is not None and vector.shape == (8,)
        assert np.isfinite(vector).all()

    extractor.analyze(project_service.repository.list_photos(project.id))
    assert encoder.image_calls == 1


def test_prompt_uses_compatible_space_and_persists_relevance(
    project_service, jpeg_bytes, tmp_path
) -> None:
    project = project_service.create_project()
    photo = project_service.import_photos(
        project.id, [PhotoUpload("photo.jpg", BytesIO(jpeg_bytes))]
    ).accepted[0]
    encoder = DeterministicVisualEncoder(dimension=8)
    extractor = FeatureExtractor(
        project_service.repository, NumpyEmbeddingCache(tmp_path / "cache"), encoder
    )
    extractor.analyze([photo])

    scores = extractor.score_prompt(project.id, "warm candid celebration")
    repeated_scores = extractor.score_prompt(project.id, "warm candid celebration")

    assert set(scores) == {photo.id}
    assert np.isfinite(scores[photo.id])
    assert repeated_scores == scores
    assert encoder.image_calls == 1
    assert encoder.text_calls == 1
    feature = project_service.repository.get_feature(photo.id)
    assert feature is not None and feature.prompt_hash and feature.brief_relevance == scores[photo.id]


def test_inference_failure_is_persisted_and_not_completed(
    project_service, jpeg_bytes, tmp_path
) -> None:
    project = project_service.create_project()
    photo = project_service.import_photos(
        project.id, [PhotoUpload("failure.jpg", BytesIO(jpeg_bytes))]
    ).accepted[0]
    encoder = DeterministicVisualEncoder(fail_names={photo.working_path.name})
    extractor = FeatureExtractor(
        project_service.repository, NumpyEmbeddingCache(tmp_path / "cache"), encoder
    )

    result = extractor.analyze([photo])

    assert result.completed == ()
    assert result.failed == (photo.id,)
    stored = project_service.repository.list_photos(project.id)[0]
    assert stored.state.value == "failed"
    assert stored.analysis_error_code == "inference_failed"
    assert project_service.repository.get_feature(photo.id) is None


def test_model_fingerprint_change_invalidates_cached_embedding(
    project_service, jpeg_bytes, tmp_path
) -> None:
    project = project_service.create_project()
    photo = project_service.import_photos(
        project.id, [PhotoUpload("photo.jpg", BytesIO(jpeg_bytes))]
    ).accepted[0]
    cache = NumpyEmbeddingCache(tmp_path / "cache")
    first = DeterministicVisualEncoder()
    FeatureExtractor(project_service.repository, cache, first).analyze([photo])

    second = DeterministicVisualEncoder()
    second.fingerprint = "deterministic-test-v2"
    FeatureExtractor(project_service.repository, cache, second).analyze(
        project_service.repository.list_photos(project.id)
    )

    feature = project_service.repository.get_feature(photo.id)
    assert second.image_calls == 1
    assert feature is not None and feature.model_fingerprint == second.fingerprint
    assert feature.prompt_hash is None and feature.brief_relevance is None
