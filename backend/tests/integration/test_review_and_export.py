"""A-08: remove suggestions without replacement, undo, and export remaining filenames."""

import csv
import hashlib
from io import BytesIO, StringIO

import pytest
from conftest import AiStack, distinct_jpegs
from PIL import Image

from selectiq.application.project_service import PhotoUpload, ProjectService
from selectiq.application.recommendation_service import RecommendationService
from selectiq.domain.errors import (
    PhotoNotFoundError,
    PhotoNotInProposalError,
    ProjectNotFoundError,
    ProposalNotFoundError,
)


def exported_rows(content: str) -> list[list[str]]:
    return list(csv.reader(StringIO(content)))[1:]


@pytest.fixture
def recommendation_service(stack: AiStack) -> RecommendationService:
    return stack.recommendations()


@pytest.fixture
def proposed(stack: AiStack, recommendation_service: RecommendationService):
    project_id = stack.analyzed_gallery(18)
    return project_id, recommendation_service.generate(project_id, 5)


def test_removing_one_reduces_the_count_without_replacement(
    recommendation_service: RecommendationService, proposed
) -> None:
    project_id, proposal = proposed
    removed_id = proposal.items[1].photo_id

    updated = recommendation_service.remove(project_id, removed_id)

    assert [item.photo_id for item in updated.items] == [item.photo_id for item in proposal.items]
    assert [item.photo_id for item in updated.selected] == [
        item.photo_id for item in proposal.items if item.photo_id != removed_id
    ]
    assert len(updated.selected) == 4
    assert updated.target_count == 5
    assert recommendation_service.current(project_id) == updated


def test_removal_is_idempotent_and_can_be_undone(
    recommendation_service: RecommendationService, proposed
) -> None:
    project_id, proposal = proposed
    photo_id = proposal.items[0].photo_id

    recommendation_service.remove(project_id, photo_id)
    assert len(recommendation_service.remove(project_id, photo_id).selected) == 4

    restored = recommendation_service.restore(project_id, photo_id)
    assert [item.photo_id for item in restored.selected] == [i.photo_id for i in proposal.items]
    assert len(recommendation_service.restore(project_id, photo_id).selected) == 5


def test_removing_all_leaves_an_empty_selection_and_header_only_export(
    recommendation_service: RecommendationService, proposed
) -> None:
    project_id, proposal = proposed
    for item in proposal.items:
        recommendation_service.remove(project_id, item.photo_id)

    assert recommendation_service.current(project_id).selected == ()
    export = recommendation_service.export(project_id)
    assert export.content.splitlines() == ["photo_id,original_filename"]
    assert export.row_count == 0


def test_export_contains_exactly_the_remaining_original_filenames(
    recommendation_service: RecommendationService, proposed
) -> None:
    project_id, proposal = proposed
    recommendation_service.remove(project_id, proposal.items[2].photo_id)

    export = recommendation_service.export(project_id)

    expected = [
        [item.photo_id, item.original_filename]
        for item in proposal.items
        if item is not proposal.items[2]
    ]
    assert exported_rows(export.content) == expected
    assert export.row_count == 4
    assert export.path.read_text(encoding="utf-8") == export.content
    assert export.filename.endswith(f"-v{proposal.version}.csv")


def test_export_never_contains_unseen_gallery_photos(
    project_service: ProjectService, recommendation_service: RecommendationService, proposed
) -> None:
    project_id, proposal = proposed
    gallery_ids = {photo.id for photo in project_service.repository.list_photos(project_id)}
    exported = {row[0] for row in exported_rows(recommendation_service.export(project_id).content)}

    assert exported == {item.photo_id for item in proposal.items}
    assert len(gallery_ids - exported) == 13


def test_duplicate_filenames_keep_separate_identity(
    stack: AiStack, recommendation_service: RecommendationService
) -> None:
    first, second = distinct_jpegs(2)
    project_id = stack.analyzed_gallery(
        target=2,
        uploads=[PhotoUpload("same.jpg", BytesIO(first)), PhotoUpload("same.jpg", BytesIO(second))],
    )
    proposal = recommendation_service.generate(project_id)
    kept, dropped = proposal.items[0].photo_id, proposal.items[1].photo_id

    recommendation_service.remove(project_id, dropped)

    assert exported_rows(recommendation_service.export(project_id).content) == [[kept, "same.jpg"]]


def test_regeneration_starts_a_fresh_full_selection(
    recommendation_service: RecommendationService, proposed
) -> None:
    project_id, proposal = proposed
    recommendation_service.remove(project_id, proposal.items[0].photo_id)

    assert len(recommendation_service.generate(project_id, 5).selected) == 5


def test_invalid_review_requests_fail_clearly(
    stack: AiStack,
    project_service: ProjectService,
    recommendation_service: RecommendationService,
    proposed,
) -> None:
    project_id, proposal = proposed
    proposed_ids = {item.photo_id for item in proposal.items}
    unproposed = next(
        photo.id
        for photo in project_service.repository.list_photos(project_id)
        if photo.id not in proposed_ids
    )
    with pytest.raises(PhotoNotInProposalError):
        recommendation_service.remove(project_id, unproposed)
    with pytest.raises(PhotoNotInProposalError):
        recommendation_service.restore(project_id, "not-a-uuid")
    with pytest.raises(ProjectNotFoundError):
        recommendation_service.export("00000000-0000-0000-0000-000000000000")

    empty = project_service.create_project()
    with pytest.raises(ProposalNotFoundError):
        recommendation_service.export(empty.id)
    with pytest.raises(ProposalNotFoundError):
        recommendation_service.remove(empty.id, proposal.items[0].photo_id)


def test_removal_in_one_project_does_not_affect_another(
    stack: AiStack, recommendation_service: RecommendationService, proposed
) -> None:
    project_id, proposal = proposed
    other = stack.analyzed_gallery(18, prefix="other")
    recommendation_service.generate(other, 5)

    with pytest.raises(PhotoNotInProposalError):
        recommendation_service.remove(other, proposal.items[0].photo_id)
    recommendation_service.remove(project_id, proposal.items[0].photo_id)

    assert len(recommendation_service.current(other).selected) == 5


def test_thumbnails_are_small_cached_jpegs_for_project_photos_only(
    project_service: ProjectService, proposed
) -> None:
    project_id, proposal = proposed
    photo_id = proposal.items[0].photo_id

    path = project_service.thumbnail(project_id, photo_id)
    with Image.open(path) as thumbnail:
        assert thumbnail.format == "JPEG"
        assert max(thumbnail.size) <= 512
    assert project_service.thumbnail(project_id, photo_id) == path

    other = project_service.create_project()
    with pytest.raises(PhotoNotFoundError):
        project_service.thumbnail(other.id, photo_id)
    with pytest.raises(PhotoNotFoundError):
        project_service.thumbnail(project_id, "../../etc/passwd")


@pytest.mark.regression
def test_review_and_export_never_modify_working_copies(
    project_service: ProjectService, recommendation_service: RecommendationService, proposed
) -> None:
    project_id, proposal = proposed
    photos = project_service.repository.list_photos(project_id)

    for item in proposal.items[:2]:
        recommendation_service.remove(project_id, item.photo_id)
    recommendation_service.restore(project_id, proposal.items[0].photo_id)
    recommendation_service.export(project_id)
    project_service.thumbnail(project_id, proposal.items[0].photo_id)

    for photo in photos:
        assert hashlib.sha256(photo.working_path.read_bytes()).hexdigest() == photo.content_hash
