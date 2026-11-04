from selectiq.intelligence.pair_selector import DeterministicPairSelector


def normalized(pair: tuple[str, str]) -> frozenset[str]:
    return frozenset(pair)


def test_selector_returns_two_distinct_photos() -> None:
    pair = DeterministicPairSelector().select(["photo-a", "photo-b", "photo-c"], set())

    assert pair is not None
    assert len(set(pair)) == 2
    assert set(pair) <= {"photo-a", "photo-b", "photo-c"}


def test_selector_is_deterministic_for_the_same_inputs() -> None:
    selector = DeterministicPairSelector()
    photo_ids = ["photo-d", "photo-b", "photo-a", "photo-c"]
    previous = {frozenset(("photo-a", "photo-b"))}

    assert selector.select(photo_ids, previous) == selector.select(photo_ids, previous)


def test_selector_never_returns_a_previous_pair_in_reverse_order() -> None:
    previous = {frozenset(("photo-a", "photo-b"))}

    pair = DeterministicPairSelector().select(["photo-a", "photo-b", "photo-c"], previous)

    assert pair is not None
    assert normalized(pair) not in previous


def test_early_pairs_balance_exposure_across_the_gallery() -> None:
    selector = DeterministicPairSelector()
    photo_ids = [f"photo-{index}" for index in range(6)]
    previous: set[frozenset[str]] = set()
    selected: list[tuple[str, str]] = []

    for _ in range(3):
        pair = selector.select(photo_ids, previous)
        assert pair is not None
        selected.append(pair)
        previous.add(normalized(pair))

    exposure = [photo_id for pair in selected for photo_id in pair]
    assert sorted(exposure) == sorted(photo_ids)


def test_selector_returns_none_when_fewer_than_two_photos_are_available() -> None:
    selector = DeterministicPairSelector()

    assert selector.select([], set()) is None
    assert selector.select(["only-photo"], set()) is None


def test_selector_returns_none_when_every_pair_has_been_used() -> None:
    photo_ids = ["photo-a", "photo-b", "photo-c"]
    previous = {
        frozenset(("photo-a", "photo-b")),
        frozenset(("photo-a", "photo-c")),
        frozenset(("photo-b", "photo-c")),
    }

    assert DeterministicPairSelector().select(photo_ids, previous) is None
