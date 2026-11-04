"""A-09: the same gallery presents the same A/B pairs in every fresh project."""

from io import BytesIO

import pytest

from conftest import AiStack, distinct_jpegs
from selectiq.application.project_service import PhotoUpload


def pair_sequence(stack: AiStack, project_id: str) -> list[tuple[str, str]]:
    filenames = {
        photo.id: photo.original_filename
        for photo in stack.projects.repository.list_photos(project_id)
    }
    sequence = []
    for _ in range(5):
        pair = stack.comparisons.next_pair(project_id)
        assert pair is not None
        sequence.append((filenames[pair.photo_a_id], filenames[pair.photo_b_id]))
        stack.comparisons.record_choice(project_id, pair.photo_a_id, pair.photo_b_id, pair.photo_a_id)
    return sequence


@pytest.mark.regression
def test_fresh_projects_with_the_same_files_see_the_same_pairs(stack: AiStack) -> None:
    first = pair_sequence(stack, stack.analyzed_gallery(18))
    second = pair_sequence(stack, stack.analyzed_gallery(18))

    assert first == second


@pytest.mark.regression
def test_upload_order_does_not_change_the_pairs(stack: AiStack) -> None:
    contents = list(enumerate(distinct_jpegs(12)))
    forward = [PhotoUpload(f"photo-{i:02d}.jpg", BytesIO(c)) for i, c in contents]
    backward = [PhotoUpload(f"photo-{i:02d}.jpg", BytesIO(c)) for i, c in reversed(contents)]

    assert pair_sequence(stack, stack.analyzed_gallery(uploads=forward)) == pair_sequence(
        stack, stack.analyzed_gallery(uploads=backward)
    )
