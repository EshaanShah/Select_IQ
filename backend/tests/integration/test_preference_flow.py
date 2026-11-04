"""A-06 red tests: saved A/B choices change project-scoped preference scores."""

from io import BytesIO

import pytest
from PIL import Image

from selectiq.application.comparison_service import ComparisonService
from selectiq.application.preference_service import PreferenceService
from selectiq.application.project_service import PhotoUpload, ProjectService
from selectiq.domain.errors import ProjectNotFoundError, ValidationError
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.model_adapters import DeterministicVisualEncoder
from selectiq.intelligence.feature_extractor import FeatureExtractor
from selectiq.intelligence.pair_selector import DeterministicPairSelector
from selectiq.intelligence.preference_model import PairwisePreferenceModel

COLORS = ["#d64545", "#45d66b", "#4561d6", "#d6c845", "#9a45d6", "#45d6cf"]


def make_jpeg(color: str = "#416b55") -> bytes:
    output = BytesIO()
    Image.new("RGB", (16, 12), color).save(output, format="JPEG")
    return output.getvalue()


@pytest.fixture
def cache(tmp_path) -> NumpyEmbeddingCache:
    return NumpyEmbeddingCache(tmp_path / "embedding-cache")


def analyzed_project(
    project_service: ProjectService, cache: NumpyEmbeddingCache, count: int = 4
) -> tuple[str, list[str]]:
    project = project_service.create_project()
    result = project_service.import_photos(
        project.id,
        [
            PhotoUpload(f"photo-{index}.jpg", BytesIO(make_jpeg(color=COLORS[index])))
            for index in range(count)
        ],
    )
    assert result.accepted_count == count
    FeatureExtractor(
        project_service.repository, cache, DeterministicVisualEncoder(dimension=8)
    ).analyze(project_service.repository.list_photos(project.id))
    return project.id, [photo.id for photo in result.accepted]


def services(
    project_service: ProjectService, cache: NumpyEmbeddingCache
) -> tuple[ComparisonService, PreferenceService]:
    comparisons = ComparisonService(
        repository=project_service.repository,
        pair_selector=DeterministicPairSelector(),
        comparison_budget=5,
    )
    preferences = PreferenceService(
        repository=project_service.repository,
        embedding_cache=cache,
        model=PairwisePreferenceModel(seed=0),
    )
    return comparisons, preferences


def test_zero_choices_give_neutral_scores_for_analyzed_photos(
    project_service: ProjectService, cache: NumpyEmbeddingCache
) -> None:
    project_id, photo_ids = analyzed_project(project_service, cache)
    _, preferences = services(project_service, cache)

    result = preferences.scores(project_id)

    assert set(result.scores) == set(photo_ids)
    assert all(score == pytest.approx(0.0) for score in result.scores.values())
    assert result.comparisons_used == 0


def test_saved_choice_raises_winner_above_loser(
    project_service: ProjectService, cache: NumpyEmbeddingCache
) -> None:
    project_id, _ = analyzed_project(project_service, cache)
    comparisons, preferences = services(project_service, cache)
    pair = comparisons.next_pair(project_id)
    assert pair is not None
    before = preferences.scores(project_id)

    comparisons.record_choice(project_id, pair.photo_a_id, pair.photo_b_id, pair.photo_b_id)
    after = preferences.scores(project_id)

    before_gap = before.scores[pair.photo_b_id] - before.scores[pair.photo_a_id]
    after_gap = after.scores[pair.photo_b_id] - after.scores[pair.photo_a_id]
    assert after_gap > before_gap
    assert after.scores[pair.photo_b_id] > after.scores[pair.photo_a_id]
    assert after.comparisons_used == 1


def test_scores_are_reproducible_across_service_instances(
    project_service: ProjectService, cache: NumpyEmbeddingCache
) -> None:
    project_id, _ = analyzed_project(project_service, cache)
    comparisons, preferences = services(project_service, cache)
    for _ in range(3):
        pair = comparisons.next_pair(project_id)
        assert pair is not None
        comparisons.record_choice(project_id, pair.photo_a_id, pair.photo_b_id, pair.photo_a_id)

    _, fresh = services(project_service, cache)

    assert preferences.scores(project_id).scores == fresh.scores(project_id).scores


def test_preferences_never_leak_across_projects(
    project_service: ProjectService, cache: NumpyEmbeddingCache
) -> None:
    first_id, _ = analyzed_project(project_service, cache)
    second_id, second_photos = analyzed_project(project_service, cache)
    comparisons, preferences = services(project_service, cache)
    second_before = preferences.scores(second_id)

    for _ in range(3):
        pair = comparisons.next_pair(first_id)
        assert pair is not None
        comparisons.record_choice(first_id, pair.photo_a_id, pair.photo_b_id, pair.photo_a_id)

    second_after = preferences.scores(second_id)
    assert set(second_after.scores) == set(second_photos)
    assert second_after.scores == second_before.scores
    assert second_after.comparisons_used == 0
    assert preferences.scores(first_id).comparisons_used == 3


def test_unanalyzed_photos_are_excluded_without_failing(
    project_service: ProjectService, cache: NumpyEmbeddingCache
) -> None:
    project_id, photo_ids = analyzed_project(project_service, cache)
    late = project_service.import_photos(
        project_id, [PhotoUpload("late.jpg", BytesIO(make_jpeg(color="#123456")))]
    )
    _, preferences = services(project_service, cache)

    result = preferences.scores(project_id)

    assert set(result.scores) == set(photo_ids)
    assert late.accepted[0].id not in result.scores


def test_missing_cached_embedding_is_excluded_without_failing(
    project_service: ProjectService, cache: NumpyEmbeddingCache
) -> None:
    project_id, photo_ids = analyzed_project(project_service, cache)
    missing_id = photo_ids[0]
    feature = project_service.repository.get_feature(missing_id)
    assert feature is not None
    feature.embedding_path.unlink()
    _, preferences = services(project_service, cache)

    result = preferences.scores(project_id)

    assert missing_id not in result.scores
    assert set(result.scores) == set(photo_ids[1:])
    assert result.comparisons_used == 0


def test_choice_with_unanalyzed_photo_is_not_used_for_training(
    project_service: ProjectService, cache: NumpyEmbeddingCache
) -> None:
    project_id, photo_ids = analyzed_project(project_service, cache)
    late = project_service.import_photos(
        project_id, [PhotoUpload("late.jpg", BytesIO(make_jpeg(color="#123456")))]
    ).accepted[0]
    comparisons, preferences = services(project_service, cache)
    comparisons.record_choice(project_id, photo_ids[0], late.id, winner_id=photo_ids[0])

    result = preferences.scores(project_id)

    assert set(result.scores) == set(photo_ids)
    assert late.id not in result.scores
    assert result.comparisons_used == 0
    assert all(score == pytest.approx(0.0) for score in result.scores.values())


def test_project_without_analysis_is_rejected(
    project_service: ProjectService, cache: NumpyEmbeddingCache
) -> None:
    project = project_service.create_project()
    project_service.import_photos(project.id, [PhotoUpload("a.jpg", BytesIO(make_jpeg()))])
    _, preferences = services(project_service, cache)

    with pytest.raises(ValidationError):
        preferences.scores(project.id)


def test_unknown_project_is_rejected(
    project_service: ProjectService, cache: NumpyEmbeddingCache
) -> None:
    _, preferences = services(project_service, cache)

    with pytest.raises(ProjectNotFoundError):
        preferences.scores("00000000-0000-0000-0000-000000000000")
