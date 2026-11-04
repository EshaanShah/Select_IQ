import csv
from io import StringIO

from selectiq.application.recommendation_service import format_selection_csv
from selectiq.domain.models import ProposalItem


def item(photo_id: str, filename: str, rank: int, removed: bool = False) -> ProposalItem:
    return ProposalItem(photo_id, filename, rank, 1.0, {}, removed=removed)


def rows(content: str) -> list[list[str]]:
    return list(csv.reader(StringIO(content)))


def test_csv_lists_remaining_photos_in_rank_order_with_ids() -> None:
    content = format_selection_csv([item("b", "two.jpg", 2), item("a", "one.jpg", 1)])
    assert rows(content) == [["photo_id", "original_filename"], ["a", "one.jpg"], ["b", "two.jpg"]]


def test_csv_excludes_removed_photos() -> None:
    content = format_selection_csv([item("a", "one.jpg", 1), item("b", "two.jpg", 2, removed=True)])
    assert rows(content) == [["photo_id", "original_filename"], ["a", "one.jpg"]]


def test_empty_selection_exports_only_the_header() -> None:
    content = format_selection_csv([item("a", "one.jpg", 1, removed=True)])
    assert rows(content) == [["photo_id", "original_filename"]]


def test_duplicate_filenames_stay_distinguishable_by_photo_id() -> None:
    content = format_selection_csv([item("a", "same.jpg", 1), item("b", "same.jpg", 2)])
    assert rows(content)[1:] == [["a", "same.jpg"], ["b", "same.jpg"]]


def test_filenames_with_commas_quotes_and_unicode_round_trip_exactly() -> None:
    names = ['finish, line.jpg', 'the "winner".jpg', "célébration.jpg"]
    content = format_selection_csv([item(str(i), name, i + 1) for i, name in enumerate(names)])
    assert [row[1] for row in rows(content)[1:]] == names
