import hashlib
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pytest

from selectiq.application.project_service import PhotoUpload, ProjectService


def test_imports_valid_and_rejects_corrupt_without_stopping(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    result = project_service.import_photos(
        project.id,
        [PhotoUpload("broken.jpg", BytesIO(b"broken")), PhotoUpload("valid.jpg", BytesIO(jpeg_bytes))],
    )
    assert result.accepted_count == 1
    assert result.accepted[0].original_filename == "valid.jpg"
    assert result.rejected[0].code == "invalid_jpeg"
    assert result.accepted[0].working_path.read_bytes() == jpeg_bytes


def test_duplicate_filenames_get_distinct_ids_and_paths(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    result = project_service.import_photos(
        project.id,
        [PhotoUpload("same.jpg", BytesIO(jpeg_bytes)), PhotoUpload("same.jpg", BytesIO(jpeg_bytes))],
    )
    first, second = result.accepted
    assert first.id != second.id
    assert first.working_path != second.working_path
    assert first.original_filename == second.original_filename == "same.jpg"


def test_accounts_for_30_photos_across_submissions(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project = project_service.create_project()
    first = project_service.import_photos(
        project.id,
        [PhotoUpload(f"photo-{index}.jpg", BytesIO(jpeg_bytes)) for index in range(15)],
    )
    second = project_service.import_photos(
        project.id,
        [PhotoUpload(f"photo-{index}.jpg", BytesIO(jpeg_bytes)) for index in range(15, 30)],
    )
    assert first.accepted_count == 15
    assert second.accepted_count == 30
    stored = project_service.repository.get(project.id)
    assert stored is not None and len(stored.photos) == 30


def test_source_hash_remains_unchanged(project_service: ProjectService, jpeg_bytes: bytes) -> None:
    source = BytesIO(jpeg_bytes)
    before = hashlib.sha256(source.getvalue()).hexdigest()
    project = project_service.create_project()
    result = project_service.import_photos(project.id, [PhotoUpload("source.jpg", source)])
    assert hashlib.sha256(source.getvalue()).hexdigest() == before
    assert result.accepted[0].content_hash == before


def test_database_failure_removes_the_orphaned_copy(
    project_service: ProjectService, jpeg_bytes: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = project_service.create_project()

    def fail_to_save(*_args, **_kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(project_service.repository, "add_photo_if_capacity", fail_to_save)
    with pytest.raises(RuntimeError, match="database unavailable"):
        project_service.import_photos(project.id, [PhotoUpload("source.jpg", BytesIO(jpeg_bytes))])

    assert list(project_service.image_store.data_root.rglob("*.jpg")) == []  # type: ignore[attr-defined]


def test_capacity_lock_prevents_concurrent_overflow(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    project_service.max_gallery_size = 1
    project = project_service.create_project()

    def upload(name: str):
        return project_service.import_photos(project.id, [PhotoUpload(name, BytesIO(jpeg_bytes))])

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(upload, ["one.jpg", "two.jpg"]))
    assert project_service.repository.accepted_count(project.id) == 1
    assert sum(len(result.accepted) for result in results) == 1
    assert [item.code for result in results for item in result.rejected] == ["gallery_limit_reached"]
