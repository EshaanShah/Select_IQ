"""Select reproducible, exposure-balanced A/B comparisons for the Alpha."""

from itertools import combinations


class DeterministicPairSelector:
    """Choose an unused pair while spreading early exposure across the gallery."""

    def select(
        self, photo_ids: list[str], previous_pairs: set[frozenset[str]]
    ) -> tuple[str, str] | None:
        identifiers = sorted(set(photo_ids))
        if len(identifiers) < 2:
            return None

        exposure = {photo_id: 0 for photo_id in identifiers}
        for previous in previous_pairs:
            for photo_id in previous:
                if photo_id in exposure:
                    exposure[photo_id] += 1

        candidates = [
            pair
            for pair in combinations(identifiers, 2)
            if frozenset(pair) not in previous_pairs
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda pair: (
                exposure[pair[0]] + exposure[pair[1]],
                max(exposure[pair[0]], exposure[pair[1]]),
                pair,
            ),
        )

