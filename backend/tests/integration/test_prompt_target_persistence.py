from io import BytesIO

from sqlalchemy import create_engine

from selectiq.application.project_service import PhotoUpload, ProjectService
from selectiq.infrastructure.image_store import LocalImageStore
from selectiq.infrastructure.project_repository import (
    Base,
    SqlProjectRepository,
    create_session_factory,
)


def make_service(database_url: str, data_root) -> ProjectService:
    repository = SqlProjectRepository(create_session_factory(database_url))
    store = LocalImageStore(data_root, 25 * 1024 * 1024, 60_000_000)
    return ProjectService(repository, store, max_gallery_size=30)


def test_prompt_and_target_survive_a_fresh_local_session(tmp_path, jpeg_bytes: bytes) -> None:
    database_url = f"sqlite:///{tmp_path / 'prompt-target.sqlite3'}"
    Base.metadata.create_all(create_engine(database_url))
    first_session = make_service(database_url, tmp_path / "files")
    project = first_session.create_project()
    first_session.import_photos(
        project.id,
        [PhotoUpload(f"photo-{index}.jpg", BytesIO(jpeg_bytes)) for index in range(6)],
    )
    prompt = "Prioritize candid emotion, relationships, and celebration."
    first_session.set_prompt_and_target(project.id, prompt, 5)

    restored = make_service(database_url, tmp_path / "files").get_project(project.id)

    assert restored.brief is not None
    assert restored.brief.original_text == prompt
    assert restored.target_count == 5


def test_prompt_and_target_are_isolated_by_project(tmp_path, jpeg_bytes: bytes) -> None:
    database_url = f"sqlite:///{tmp_path / 'project-isolation.sqlite3'}"
    Base.metadata.create_all(create_engine(database_url))
    service = make_service(database_url, tmp_path / "files")
    first = service.create_project()
    second = service.create_project()
    for project in (first, second):
        service.import_photos(
            project.id,
            [PhotoUpload(f"photo-{index}.jpg", BytesIO(jpeg_bytes)) for index in range(5)],
        )

    service.set_prompt_and_target(first.id, "Sports action and athlete emotion.", 3)
    service.set_prompt_and_target(second.id, "Relationships and respectful portraits.", 4)

    restored_first = service.get_project(first.id)
    restored_second = service.get_project(second.id)
    assert restored_first.brief is not None
    assert restored_second.brief is not None
    assert restored_first.brief.original_text == "Sports action and athlete emotion."
    assert restored_first.target_count == 3
    assert restored_second.brief.original_text == "Relationships and respectful portraits."
    assert restored_second.target_count == 4
