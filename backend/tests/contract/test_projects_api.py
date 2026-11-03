from io import BytesIO

from fastapi.testclient import TestClient

from selectiq.api.main import create_app
from selectiq.api.routes.projects import project_service as project_service_dependency
from selectiq.application.project_service import ProjectService


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
    assert status.json()["remainingCapacity"] == 299


def test_unknown_project_and_missing_files_are_reported(project_service: ProjectService) -> None:
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    client = TestClient(app)
    assert client.post("/projects/not-a-project/photos", files=[]).status_code == 422
    assert client.get("/projects/not-a-project/status").status_code == 404
