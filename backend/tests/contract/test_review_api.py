import csv
from io import StringIO

import pytest
from conftest import AiStack
from fastapi.testclient import TestClient

from selectiq.api.main import create_app
from selectiq.api.routes.projects import project_service as project_service_dependency
from selectiq.api.routes.recommendations import (
    recommendation_service as recommendation_service_dependency,
)
from selectiq.application.project_service import ProjectService


@pytest.fixture
def client(project_service: ProjectService, stack: AiStack):
    service = stack.recommendations()
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    app.dependency_overrides[recommendation_service_dependency] = lambda: service
    return TestClient(app)


@pytest.fixture
def proposal(client: TestClient, stack: AiStack) -> dict:
    project_id = stack.analyzed_gallery(18)
    return client.post(f"/projects/{project_id}/recommendations").json()


def selection_url(proposal: dict, photo_id: str) -> str:
    return f"/projects/{proposal['projectId']}/recommendations/selection/{photo_id}"


def test_remove_and_restore_return_the_updated_proposal(client: TestClient, proposal: dict) -> None:
    photo_id = proposal["recommendations"][0]["photoId"]

    removed = client.delete(selection_url(proposal, photo_id))
    assert removed.status_code == 200
    assert removed.json()["selectedCount"] == 4
    assert removed.json()["removedCount"] == 1
    assert removed.json()["targetCount"] == 5
    assert removed.json()["recommendations"][0]["removed"] is True
    assert len(removed.json()["recommendations"]) == 5

    restored = client.post(f"{selection_url(proposal, photo_id)}/restore")
    assert restored.status_code == 200
    assert restored.json()["selectedCount"] == 5
    assert restored.json()["recommendations"][0]["removed"] is False


def test_export_downloads_a_csv_of_remaining_photos(client: TestClient, proposal: dict) -> None:
    removed_id = proposal["recommendations"][3]["photoId"]
    client.delete(selection_url(proposal, removed_id))

    response = client.get(f"/projects/{proposal['projectId']}/recommendations/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert ".csv" in response.headers["content-disposition"]
    rows = list(csv.reader(StringIO(response.text)))
    assert rows[0] == ["photo_id", "original_filename"]
    assert rows[1:] == [
        [item["photoId"], item["originalFilename"]]
        for item in proposal["recommendations"]
        if item["photoId"] != removed_id
    ]


def test_review_errors(client: TestClient, proposal: dict, project_service: ProjectService) -> None:
    missing_photo = "00000000-0000-0000-0000-000000000000"
    assert client.delete(selection_url(proposal, missing_photo)).status_code == 404
    assert client.post(f"{selection_url(proposal, missing_photo)}/restore").status_code == 404
    assert client.get("/projects/not-a-project/recommendations/export").status_code == 404
    empty = project_service.create_project()
    assert client.get(f"/projects/{empty.id}/recommendations/export").status_code == 404


def test_thumbnail_serves_a_jpeg_for_project_photos(client: TestClient, proposal: dict) -> None:
    photo_id = proposal["recommendations"][0]["photoId"]
    url = f"/projects/{proposal['projectId']}/photos/{photo_id}/thumbnail"

    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content[:2] == b"\xff\xd8"
    other = f"/projects/00000000-0000-0000-0000-000000000000/photos/{photo_id}/thumbnail"
    assert client.get(other).status_code == 404


def test_cors_allows_the_review_methods(client: TestClient, proposal: dict) -> None:
    response = client.options(
        selection_url(proposal, proposal["recommendations"][0]["photoId"]),
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "DELETE"},
    )
    assert response.status_code == 200
    assert "DELETE" in response.headers["access-control-allow-methods"]
