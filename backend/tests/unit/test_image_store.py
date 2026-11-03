from io import BytesIO

import pytest

from selectiq.domain.errors import ImportValidationError
from selectiq.infrastructure.image_store import LocalImageStore


def test_valid_jpeg_is_staged_and_preserves_bytes(tmp_path, jpeg_bytes: bytes) -> None:
    store = LocalImageStore(tmp_path, max_file_size_bytes=10_000, max_decoded_pixels=1_000)
    staged = store.stage_upload("project", "portrait.JPG", BytesIO(jpeg_bytes))
    final = store.finalize("project", "photo", staged)

    assert final.read_bytes() == jpeg_bytes
    assert staged.width == 16
    assert staged.height == 12
    assert final.name == "portrait.JPG"


@pytest.mark.parametrize("filename", ["photo.png", "photo.jfif", "photo.heic"])
def test_unsupported_extensions_have_a_defined_error(tmp_path, filename: str) -> None:
    store = LocalImageStore(tmp_path, 100, 100)
    with pytest.raises(ImportValidationError) as caught:
        store.stage_upload("project", filename, BytesIO(b"not an image"))
    assert caught.value.code == "unsupported_file_type"


def test_corrupt_jpeg_is_rejected_and_temporary_file_removed(tmp_path) -> None:
    store = LocalImageStore(tmp_path, 100, 100)
    with pytest.raises(ImportValidationError) as caught:
        store.stage_upload("project", "broken.jpg", BytesIO(b"not an image"))
    assert caught.value.code == "invalid_jpeg"
    assert list(tmp_path.rglob("*.part")) == []


def test_file_size_limit_is_streamed(tmp_path, jpeg_bytes: bytes) -> None:
    store = LocalImageStore(tmp_path, len(jpeg_bytes) - 1, 1_000)
    with pytest.raises(ImportValidationError) as caught:
        store.stage_upload("project", "large.jpg", BytesIO(jpeg_bytes))
    assert caught.value.code == "file_too_large"


def test_pixel_limit_is_checked_after_decode(tmp_path, jpeg_bytes: bytes) -> None:
    store = LocalImageStore(tmp_path, 10_000, 100)
    with pytest.raises(ImportValidationError) as caught:
        store.stage_upload("project", "large.jpg", BytesIO(jpeg_bytes))
    assert caught.value.code == "pixel_limit_exceeded"


def test_client_paths_cannot_escape_photo_directory(tmp_path, jpeg_bytes: bytes) -> None:
    store = LocalImageStore(tmp_path, 10_000, 1_000)
    staged = store.stage_upload("project", "../../portrait.jpg", BytesIO(jpeg_bytes))
    final = store.finalize("project", "photo", staged)
    assert final == tmp_path / "projects" / "project" / "sources" / "photo" / "portrait.jpg"
