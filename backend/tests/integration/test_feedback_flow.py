"""A-10 satisfaction persistence and project-linkage tests written before implementation."""

from importlib import import_module

import pytest

from selectiq.domain.errors import ProjectNotFoundError, ValidationError
from selectiq.infrastructure.project_repository import SqlProposalRepository

def feedback_service(project_service):
    """Load the future A-10 types at test time so every case is collected in the red phase."""
    application = import_module("selectiq.application.feedback_service")
    infrastructure = import_module("selectiq.infrastructure.project_repository")
    repository_type = getattr(infrastructure, "SqlFeedbackRepository")
    service_type = getattr(application, "FeedbackService")
    session_factory = project_service.repository.session_factory
    return service_type(
        project_service.repository,
        SqlProposalRepository(session_factory),
        repository_type(session_factory),
    )


def completed_project(stack) -> str:
    project_id = stack.analyzed_gallery(10, target=3)
    stack.recommendations().generate(project_id)
    return project_id


def test_stores_a_valid_rating_and_comment_for_the_completed_project(stack) -> None:
    project_id = completed_project(stack)
    service = feedback_service(stack.projects)

    saved = service.submit(project_id, 4, "The emotional moments were selected well.")

    assert saved.project_id == project_id
    assert saved.rating == 4
    assert saved.comment == "The emotional moments were selected well."
    assert saved.created_at is not None


@pytest.mark.parametrize("rating", [1, 5])
def test_accepts_both_rating_boundaries(stack, rating: int) -> None:
    project_id = completed_project(stack)

    saved = feedback_service(stack.projects).submit(project_id, rating, None)

    assert saved.rating == rating


def test_comment_is_optional(stack) -> None:
    project_id = completed_project(stack)

    saved = feedback_service(stack.projects).submit(project_id, 5, None)

    assert saved.comment is None


def test_preserves_unicode_and_user_text(stack) -> None:
    project_id = completed_project(stack)
    comment = "Très utile — 情感时刻 were preserved 📷"

    saved = feedback_service(stack.projects).submit(project_id, 4, comment)

    assert saved.comment == comment


@pytest.mark.parametrize("rating", [0, 6])
def test_rejects_out_of_range_ratings_without_storing_feedback(stack, rating: int) -> None:
    project_id = completed_project(stack)
    service = feedback_service(stack.projects)

    with pytest.raises(ValidationError, match="between 1 and 5"):
        service.submit(project_id, rating, None)

    assert service.current(project_id) is None


def test_rejects_an_unknown_project_without_creating_an_orphan_record(stack) -> None:
    service = feedback_service(stack.projects)

    with pytest.raises(ProjectNotFoundError):
        service.submit("00000000-0000-0000-0000-000000000000", 4, None)


def test_rejects_feedback_until_the_project_has_a_proposal(stack) -> None:
    project_id = stack.analyzed_gallery(10, target=3)
    service = feedback_service(stack.projects)

    with pytest.raises(ValidationError, match="proposal"):
        service.submit(project_id, 4, None)

    assert service.current(project_id) is None


def test_feedback_never_leaks_between_projects(stack) -> None:
    first = completed_project(stack)
    second = completed_project(stack)
    service = feedback_service(stack.projects)

    service.submit(first, 4, "First project only")

    assert service.current(first).comment == "First project only"
    assert service.current(second) is None


def test_feedback_persists_across_service_instances(stack) -> None:
    project_id = completed_project(stack)
    first = feedback_service(stack.projects)
    first.submit(project_id, 5, "Persist this response")

    restored = feedback_service(stack.projects).current(project_id)

    assert restored is not None
    assert restored.rating == 5
    assert restored.comment == "Persist this response"


