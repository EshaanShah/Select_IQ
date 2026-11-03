from io import BytesIO

import pytest

from selectiq.application.project_service import PhotoUpload, ProjectService
from selectiq.domain.errors import ValidationError


def add_photos(service: ProjectService, project_id: str, jpeg_bytes: bytes, count: int) -> None:
    result = service.import_photos(
        project_id,
        [PhotoUpload(f"photo-{index}.jpg", BytesIO(jpeg_bytes)) for index in range(count)],
    )
    assert result.accepted_count == count


def test_valid_prompt_and_target_are_stored(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 15)

    updated = project_service.set_prompt_and_target(
        project.id, "Prioritize candid emotion and quiet storytelling.", 5
    )

    assert updated.brief is not None
    assert updated.brief.original_text == "Prioritize candid emotion and quiet storytelling."
    assert updated.target_count == 5


@pytest.mark.parametrize("accepted_count", [15, 20])
def test_demo_target_five_is_valid_for_demo_gallery_sizes(
    project_service: ProjectService, jpeg_bytes: bytes, accepted_count: int
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, accepted_count)

    updated = project_service.set_prompt_and_target(project.id, "Tell the full story.", 5)

    assert updated.target_count == 5


@pytest.mark.parametrize("prompt", ["", " ", "\t\n", "\u2003\u2009"])
def test_blank_or_whitespace_only_prompt_is_rejected(
    project_service: ProjectService, jpeg_bytes: bytes, prompt: str
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 1)

    with pytest.raises(ValidationError, match="(?i)prompt.*blank|blank.*prompt"):
        project_service.set_prompt_and_target(project.id, prompt, 1)


@pytest.mark.parametrize("target", [0, -1, -100])
def test_nonpositive_target_is_rejected(
    project_service: ProjectService, jpeg_bytes: bytes, target: int
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 5)

    with pytest.raises(ValidationError, match="(?i)target.*(positive|at least 1)"):
        project_service.set_prompt_and_target(project.id, "Keep emotional moments.", target)


@pytest.mark.parametrize("target", [1.5, "2", True, None])
def test_target_must_be_an_integer_without_type_coercion(
    project_service: ProjectService, jpeg_bytes: bytes, target: object
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 5)

    with pytest.raises(ValidationError, match="(?i)target.*integer"):
        project_service.set_prompt_and_target(  # type: ignore[arg-type]
            project.id, "Keep emotional moments.", target
        )


def test_target_cannot_exceed_accepted_photo_count(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 4)

    with pytest.raises(ValidationError, match="(?i)target.*accepted"):
        project_service.set_prompt_and_target(project.id, "Keep emotional moments.", 5)


def test_target_equal_to_accepted_photo_count_is_valid(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 5)

    updated = project_service.set_prompt_and_target(project.id, "Keep every moment.", 5)

    assert updated.target_count == 5


def test_target_is_rejected_when_project_has_no_accepted_photos(
    project_service: ProjectService,
) -> None:
    project = project_service.create_project()

    with pytest.raises(ValidationError, match="(?i)(accepted photo|upload)"):
        project_service.set_prompt_and_target(project.id, "Keep the best moment.", 1)


def test_nonblank_unicode_prompt_is_preserved_exactly(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 1)
    prompt = "  Prioritize Jos\u00e9’s joy 🎉 and the family’s quiet moments.  "

    updated = project_service.set_prompt_and_target(project.id, prompt, 1)

    assert updated.brief is not None
    assert updated.brief.original_text == prompt


def test_replacing_prompt_and_target_updates_both_values(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 5)
    project_service.set_prompt_and_target(project.id, "First direction", 2)

    updated = project_service.set_prompt_and_target(project.id, "Revised direction", 4)

    assert updated.brief is not None
    assert updated.brief.original_text == "Revised direction"
    assert updated.target_count == 4


def test_invalid_update_does_not_partially_replace_saved_values(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    add_photos(project_service, project.id, jpeg_bytes, 5)
    project_service.set_prompt_and_target(project.id, "Original direction", 3)

    with pytest.raises(ValidationError):
        project_service.set_prompt_and_target(project.id, "Invalid replacement", 6)

    restored = project_service.get_project(project.id)
    assert restored.brief is not None
    assert restored.brief.original_text == "Original direction"
    assert restored.target_count == 3
