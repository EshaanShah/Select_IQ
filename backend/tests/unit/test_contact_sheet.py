from io import BytesIO

import pytest
from PIL import Image

from selectiq.infrastructure.contact_sheet import ContactSheetError, build_contact_sheets


def write_photos(tmp_path, count: int) -> list[tuple[str, object]]:
    items = []
    for index in range(count):
        path = tmp_path / f"photo-{index}.jpg"
        Image.new("RGB", (640, 480), (index * 8 % 255, 90, 140)).save(path, "JPEG")
        items.append((f"P{index + 1:02d}", path))
    return items


def test_thirty_photos_fit_in_three_labeled_jpeg_sheets(tmp_path) -> None:
    sheets = build_contact_sheets(write_photos(tmp_path, 30))

    assert len(sheets) == 3
    for sheet in sheets:
        assert len(sheet) < 4 * 1024 * 1024
        with Image.open(BytesIO(sheet)) as image:
            assert image.format == "JPEG"
            assert max(image.size) <= 2048


def test_small_gallery_uses_a_single_sheet(tmp_path) -> None:
    assert len(build_contact_sheets(write_photos(tmp_path, 5))) == 1


def test_gallery_beyond_sheet_capacity_is_rejected(tmp_path) -> None:
    with pytest.raises(ContactSheetError):
        build_contact_sheets(write_photos(tmp_path, 4), per_sheet=1, max_sheets=3)


def test_empty_gallery_is_rejected() -> None:
    with pytest.raises(ContactSheetError):
        build_contact_sheets([])
