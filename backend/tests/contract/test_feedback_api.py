"""A-10 API contract written before satisfaction feedback is implemented."""

import pytest
from fastapi.testclient import TestClient

from selectiq.api.main import create_app


PROJECT_ID = "00000000-0000-0000-0000-000000000001"


def client() -> TestClient:
    return TestClient(create_app())


def test_feedback_route_accepts_a_rating_and_optional_comment() -> None:
    response = client().post(
        f"/projects/{PROJECT_ID}/feedback",
        json={"rating": 4, "comment": "The emotional moments were selected well."},
    )

    # This begins red because A-10 has no route or persistence implementation yet.
    assert response.status_code != 404


@pytest.mark.parametrize("rating", [0, 6])
def test_feedback_route_rejects_ratings_outside_one_through_five(rating: int) -> None:
    response = client().post(
        f"/projects/{PROJECT_ID}/feedback",
        json={"rating": rating},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("rating", [True, 4.5, "5", None])
def test_feedback_route_requires_a_strict_integer_rating(rating: object) -> None:
    response = client().post(
        f"/projects/{PROJECT_ID}/feedback",
        json={"rating": rating},
    )

    assert response.status_code == 422


def test_feedback_route_requires_a_rating() -> None:
    response = client().post(
        f"/projects/{PROJECT_ID}/feedback",
        json={"comment": "A comment without a rating."},
    )

    assert response.status_code == 422


