from io import BytesIO

import pytest

from selectiq.application.comparison_service import ComparisonService
from selectiq.application.project_service import PhotoUpload, ProjectService
from selectiq.domain.errors import ProjectNotFoundError, ValidationError
from selectiq.domain.enums import ProcessingState
from selectiq.intelligence.pair_selector import DeterministicPairSelector


def add_photos(
    service: ProjectService, project_id: str, jpeg_bytes: bytes, count: int
) -> list[str]:
    result = service.import_photos(
        project_id,
        [PhotoUpload(f"photo-{index}.jpg", BytesIO(jpeg_bytes)) for index in range(count)],
    )
    assert result.accepted_count == count
    return [photo.id for photo in result.accepted]


def comparison_service(project_service: ProjectService, budget: int = 5) -> ComparisonService:
    return ComparisonService(
        repository=project_service.repository,
        pair_selector=DeterministicPairSelector(),
        comparison_budget=budget,
    )


def test_next_pair_contains_two_distinct_current_project_photos(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    photo_ids = set(add_photos(project_service, project.id, jpeg_bytes, 4))

    pair = comparison_service(project_service).next_pair(project.id)

    assert pair is not None
    assert pair.photo_a_id != pair.photo_b_id
    assert {pair.photo_a_id, pair.photo_b_id} <= photo_ids
    assert pair.sequence == 1
    assert pair.budget == 5


def test_choice_records_winner_loser_project_and_sequence(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 4)
    service = comparison_service(project_service)
    pair = service.next_pair(project.id)
    assert pair is not None

    choice = service.record_choice(
        project.id, pair.photo_a_id, pair.photo_b_id, winner_id=pair.photo_a_id
    )

    assert choice.project_id == project.id
    assert choice.winner_id == pair.photo_a_id
    assert choice.loser_id == pair.photo_b_id
    assert choice.sequence == 1
    assert service.choices(project.id) == [choice]


def test_losing_photo_remains_eligible_and_unchanged(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 3)
    service = comparison_service(project_service)
    pair = service.next_pair(project.id)
    assert pair is not None
    service.record_choice(project.id, pair.photo_a_id, pair.photo_b_id, pair.photo_a_id)

    restored = project_service.get_project(project.id)
    loser = next(photo for photo in restored.photos if photo.id == pair.photo_b_id)
    assert loser.state == ProcessingState.PENDING
    assert loser in restored.photos


@pytest.mark.parametrize("unknown_position", ["photo_a", "photo_b", "winner"])
def test_unknown_photo_id_is_rejected(
    project_service: ProjectService, jpeg_bytes: bytes, unknown_position: str
) -> None:
    project = project_service.create_project()
    first, second = add_photos(project_service, project.id, jpeg_bytes, 2)
    values = {"photo_a": first, "photo_b": second, "winner": first}
    values[unknown_position] = "00000000-0000-0000-0000-000000000000"

    with pytest.raises(ValidationError, match="(?i)photo.*project|unknown.*photo"):
        comparison_service(project_service).record_choice(
            project.id, values["photo_a"], values["photo_b"], values["winner"]
        )


def test_same_photo_cannot_be_compared_with_itself(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    photo_id = add_photos(project_service, project.id, jpeg_bytes, 1)[0]

    with pytest.raises(ValidationError, match="(?i)distinct|same photo"):
        comparison_service(project_service).record_choice(
            project.id, photo_id, photo_id, winner_id=photo_id
        )


def test_winner_must_be_one_of_the_presented_photos(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    first, second, third = add_photos(project_service, project.id, jpeg_bytes, 3)

    with pytest.raises(ValidationError, match="(?i)winner.*presented|winner.*pair"):
        comparison_service(project_service).record_choice(
            project.id, first, second, winner_id=third
        )


def test_photo_from_another_project_is_rejected(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    first_project = project_service.create_project()
    second_project = project_service.create_project()
    first_photo = add_photos(project_service, first_project.id, jpeg_bytes, 1)[0]
    second_photo = add_photos(project_service, second_project.id, jpeg_bytes, 1)[0]

    with pytest.raises(ValidationError, match="(?i)photo.*project"):
        comparison_service(project_service).record_choice(
            first_project.id, first_photo, second_photo, winner_id=first_photo
        )


def test_reversed_duplicate_pair_is_rejected(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    first, second = add_photos(project_service, project.id, jpeg_bytes, 2)
    service = comparison_service(project_service)
    service.record_choice(project.id, first, second, winner_id=first)

    with pytest.raises(ValidationError, match="(?i)already.*compared|duplicate.*pair"):
        service.record_choice(project.id, second, first, winner_id=second)


def test_sequence_increments_and_flow_stops_at_demo_budget(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 6)
    service = comparison_service(project_service, budget=5)

    for expected_sequence in range(1, 6):
        pair = service.next_pair(project.id)
        assert pair is not None
        assert pair.sequence == expected_sequence
        choice = service.record_choice(
            project.id, pair.photo_a_id, pair.photo_b_id, winner_id=pair.photo_a_id
        )
        assert choice.sequence == expected_sequence

    assert len(service.choices(project.id)) == 5
    assert service.next_pair(project.id) is None


def test_choices_never_leak_between_projects(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    first_project = project_service.create_project()
    second_project = project_service.create_project()
    add_photos(project_service, first_project.id, jpeg_bytes, 2)
    add_photos(project_service, second_project.id, jpeg_bytes, 2)
    service = comparison_service(project_service)
    pair = service.next_pair(first_project.id)
    assert pair is not None
    service.record_choice(
        first_project.id, pair.photo_a_id, pair.photo_b_id, winner_id=pair.photo_a_id
    )

    assert len(service.choices(first_project.id)) == 1
    assert service.choices(second_project.id) == []


def test_unknown_project_is_rejected(project_service: ProjectService) -> None:
    with pytest.raises(ProjectNotFoundError):
        comparison_service(project_service).next_pair(
            "00000000-0000-0000-0000-000000000000"
        )
