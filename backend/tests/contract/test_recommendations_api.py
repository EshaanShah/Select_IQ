import pytest
from conftest import AiStack
from fastapi.testclient import TestClient

from selectiq.api.main import create_app
from selectiq.api.routes.recommendations import (
    recommendation_service as recommendation_service_dependency,
)


@pytest.fixture
def client(stack: AiStack) -> TestClient:
    app = create_app()
    app.dependency_overrides[recommendation_service_dependency] = lambda: stack.recommendations()
    return TestClient(app)


@pytest.fixture
def project_id(stack: AiStack) -> str:
    return stack.analyzed_gallery(18)


def test_generate_returns_the_proposal_contract(client: TestClient, project_id: str) -> None:
    response = client.post(f"/projects/{project_id}/recommendations")

    assert response.status_code == 201
    body = response.json()
    assert body["projectId"] == project_id
    assert body["version"] == 1
    assert body["targetCount"] == 5
    assert body["selectedCount"] == 5
    assert body["isGenuineAi"] is False
    provenance = body["provenance"]
    assert provenance["kind"] == "test_signals"
    assert provenance["label"].startswith("Test signals (not AI)")
    assert provenance["guidanceStatus"] == "completed"
    assert provenance["comparisonsUsed"] == 0
    assert provenance["excludedPhotoCount"] == 0
    assert set(body["parameters"]["weights"]) == {"prompt_relevance", "ai_guidance", "preference"}
    assert [item["rank"] for item in body["recommendations"]] == [1, 2, 3, 4, 5]
    first = body["recommendations"][0]
    assert set(first) == {"photoId", "originalFilename", "rank", "score", "contributions"}
    assert set(first["contributions"]) == {"promptRelevance", "aiGuidance", "preference"}
    assert "working_path" not in response.text and "storage" not in response.text


def test_read_returns_the_latest_proposal(client: TestClient, project_id: str) -> None:
    assert client.get(f"/projects/{project_id}/recommendations").status_code == 404
    client.post(f"/projects/{project_id}/recommendations", json={"targetCount": 3})
    created = client.post(f"/projects/{project_id}/recommendations")

    latest = client.get(f"/projects/{project_id}/recommendations")

    assert latest.status_code == 200
    assert latest.json() == created.json()
    assert latest.json()["version"] == 2


@pytest.mark.parametrize("target", [0, -1, 2.5, "5", 19])
def test_invalid_targets_are_rejected(client: TestClient, project_id: str, target) -> None:
    response = client.post(f"/projects/{project_id}/recommendations", json={"targetCount": target})
    assert response.status_code == 422


def test_too_large_target_explains_the_limit(client: TestClient, project_id: str) -> None:
    response = client.post(f"/projects/{project_id}/recommendations", json={"targetCount": 19})
    assert response.json()["detail"] == "Target must be between 1 and 18 photographs."


def test_unanalyzed_gallery_is_rejected_with_the_next_step(
    client: TestClient, stack: AiStack
) -> None:
    project = stack.projects.create_project()
    response = client.post(f"/projects/{project.id}/recommendations")
    assert response.status_code == 422
    assert "Save a creative brief and target" in response.json()["detail"]


def test_unknown_project_is_not_found(client: TestClient) -> None:
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/projects/{missing}/recommendations").status_code == 404
    assert client.get(f"/projects/{missing}/recommendations").status_code == 404
    assert client.get("/projects/not-a-uuid/recommendations").status_code == 404
