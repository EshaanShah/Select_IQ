from selectiq.domain.models import Project


def test_new_project_starts_without_photos_or_target() -> None:
    project = Project(id="project-1")

    assert project.photos == []
    assert project.target_count is None

