"""A-10 API contract written before satisfaction feedback is implemented."""

import pytest
from fastapi.testclient import TestClient

from selectiq.api.main import create_app
from selectiq.api.routes import feedback
from selectiq.domain.errors import ProjectNotFoundError, ValidationError
from selectiq.domain.models import SatisfactionFeedback

PROJECT_ID = "00000000-0000-0000-0000-000000000001"


def client(service: object | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[feedback.feedback_service] = lambda: service or StubFeedbackService()
    return TestClient(app)


class StubFeedbackService:
    def submit(self, project_id: str, rating: int, comment: str | None) -> SatisfactionFeedback:
        return SatisfactionFeedback(project_id, rating, comment)


class RejectingFeedbackService:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def submit(self, project_id: str, rating: int, comment: str | None) -> SatisfactionFeedback:
        raise self.error


def test_feedback_route_accepts_a_rating_and_optional_comment() -> None:
    response = client().post(
        f"/projects/{PROJECT_ID}/feedback",
        json={"rating": 4, "comment": "The emotional moments were selected well."},
    )

    assert response.status_code == 201
    assert response.json() == {
        "projectId": PROJECT_ID,
        "rating": 4,
        "comment": "The emotional moments were selected well.",
        "createdAt": None,
    }


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


def test_feedback_route_reports_an_unknown_project() -> None:
    response = client(
        RejectingFeedbackService(ProjectNotFoundError("Project was not found."))
    ).post(f"/projects/{PROJECT_ID}/feedback", json={"rating": 4})

    assert response.status_code == 404
    assert response.json()["detail"] == "Project was not found."


def test_feedback_route_requires_a_completed_proposal() -> None:
    response = client(
        RejectingFeedbackService(ValidationError("Generate a proposal before submitting feedback."))
    ).post(f"/projects/{PROJECT_ID}/feedback", json={"rating": 4})

    assert response.status_code == 409
    assert response.json()["detail"] == "Generate a proposal before submitting feedback."


