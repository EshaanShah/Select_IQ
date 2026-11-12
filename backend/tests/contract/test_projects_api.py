from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from selectiq.api.main import create_app
from selectiq.api.routes.projects import project_service as project_service_dependency
from selectiq.application.project_service import ProjectService


def create_project_with_photos(client: TestClient, jpeg_bytes: bytes, count: int) -> str:
    project_id = client.post("/projects").json()["projectId"]
    response = client.post(
        f"/projects/{project_id}/photos",
        files=[
            ("files", (f"photo-{index}.jpg", BytesIO(jpeg_bytes), "image/jpeg"))
            for index in range(count)
        ],
    )
    assert response.status_code == 200
    assert response.json()["acceptedCount"] == count
    return project_id


def test_project_upload_contract(project_service: ProjectService, jpeg_bytes: bytes) -> None:
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    client = TestClient(app)
    created = client.post("/projects")
    project_id = created.json()["projectId"]
    response = client.post(
        f"/projects/{project_id}/photos",
        files=[
            ("files", ("valid.jpg", BytesIO(jpeg_bytes), "image/jpeg")),
            ("files", ("notes.png", BytesIO(b"png"), "image/png")),
        ],
    )
    assert created.status_code == 201
    assert response.status_code == 200
    assert response.json()["batchAcceptedCount"] == 1
    assert response.json()["batchRejectedCount"] == 1
    assert response.json()["rejected"][0]["code"] == "unsupported_file_type"
    assert "working_path" not in response.text
    status = client.get(f"/projects/{project_id}/status")
    assert status.json()["acceptedCount"] == 1
    assert status.json()["remainingCapacity"] == 29
    assert status.json()["photos"] == [
        {
            "photoId": response.json()["accepted"][0]["photoId"],
            "originalFilename": "valid.jpg",
            "width": 16,
            "height": 12,
            "byteSize": len(jpeg_bytes),
            "state": "pending",
            "thumbnailUrl": (
                f"/projects/{project_id}/photos/"
                f"{response.json()['accepted'][0]['photoId']}/thumbnail"
            ),
            "analysisErrorCode": None,
            "analysisErrorMessage": None,
        }
    ]


def test_unknown_project_and_missing_files_are_reported(project_service: ProjectService) -> None:
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    client = TestClient(app)
    assert client.post("/projects/not-a-project/photos", files=[]).status_code == 422
    assert client.get("/projects/not-a-project/status").status_code == 404


def test_prompt_and_target_contract_persists_and_reloads(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    client = TestClient(app)
    project_id = create_project_with_photos(client, jpeg_bytes, 15)
    prompt = "Prioritize candid emotion and energetic action."

    saved = client.post(
        f"/projects/{project_id}/brief",
        json={"prompt": prompt, "target": 5},
    )

    assert saved.status_code == 200
    assert saved.json() == {
        "projectId": project_id,
        "prompt": prompt,
        "target": 5,
        "acceptedCount": 15,
    }
    restored = client.get(f"/projects/{project_id}/status")
    assert restored.status_code == 200
    assert restored.json()["prompt"] == prompt
    assert restored.json()["target"] == 5


def test_status_uses_null_for_prompt_and_target_before_they_are_set(
    project_service: ProjectService,
) -> None:
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    client = TestClient(app)
    project_id = client.post("/projects").json()["projectId"]

    response = client.get(f"/projects/{project_id}/status")

    assert response.status_code == 200
    assert response.json()["prompt"] is None
    assert response.json()["target"] is None


def test_blank_prompt_returns_a_clear_client_error(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    client = TestClient(app)
    project_id = create_project_with_photos(client, jpeg_bytes, 5)

    response = client.post(
        f"/projects/{project_id}/brief", json={"prompt": " \t\n", "target": 2}
    )

    assert response.status_code == 422
    assert "prompt" in response.text.lower()
    assert "blank" in response.text.lower()


@pytest.mark.parametrize("target", [0, -1, 6])
def test_out_of_range_target_returns_a_clear_client_error(
    project_service: ProjectService, jpeg_bytes: bytes, target: int
) -> None:
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    client = TestClient(app)
    project_id = create_project_with_photos(client, jpeg_bytes, 5)

    response = client.post(
        f"/projects/{project_id}/brief",
        json={"prompt": "Keep the strongest moments.", "target": target},
    )

    assert response.status_code == 422
    assert "target" in response.text.lower()


@pytest.mark.parametrize("target", [2.5, "2", True, None])
def test_target_contract_rejects_nonintegers_without_coercion(
    project_service: ProjectService, jpeg_bytes: bytes, target: object
) -> None:
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    client = TestClient(app)
    project_id = create_project_with_photos(client, jpeg_bytes, 5)

    response = client.post(
        f"/projects/{project_id}/brief",
        json={"prompt": "Keep the strongest moments.", "target": target},
    )

    assert response.status_code == 422
    assert "target" in response.text.lower()


def test_unknown_project_cannot_store_prompt_and_target(
    project_service: ProjectService,
) -> None:
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    client = TestClient(app)

    response = client.post(
        "/projects/00000000-0000-0000-0000-000000000000/brief",
        json={"prompt": "Keep the strongest moments.", "target": 1},
    )

    assert response.status_code == 404
