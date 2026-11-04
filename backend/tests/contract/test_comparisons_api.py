from io import BytesIO

from fastapi.testclient import TestClient

from selectiq.api.main import create_app
from selectiq.api.routes.comparisons import comparison_service as comparison_service_dependency
from selectiq.api.routes.projects import project_service as project_service_dependency
from selectiq.application.comparison_service import ComparisonService
from selectiq.application.project_service import ProjectService
from selectiq.intelligence.pair_selector import DeterministicPairSelector


def make_client(project_service: ProjectService) -> TestClient:
    app = create_app()
    service = ComparisonService(
        repository=project_service.repository,
        pair_selector=DeterministicPairSelector(),
        comparison_budget=5,
    )
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    app.dependency_overrides[comparison_service_dependency] = lambda: service
    return TestClient(app)


def create_project_with_photos(
    client: TestClient, jpeg_bytes: bytes, count: int
) -> tuple[str, list[str]]:
    project_id = client.post("/projects").json()["projectId"]
    uploaded = client.post(
        f"/projects/{project_id}/photos",
        files=[
            ("files", (f"photo-{index}.jpg", BytesIO(jpeg_bytes), "image/jpeg"))
            for index in range(count)
        ],
    )
    assert uploaded.status_code == 200
    return project_id, [photo["photoId"] for photo in uploaded.json()["accepted"]]


def test_next_pair_contract_returns_two_renderable_project_photos(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    client = make_client(project_service)
    project_id, photo_ids = create_project_with_photos(client, jpeg_bytes, 3)

    response = client.get(f"/projects/{project_id}/comparisons/next")

    assert response.status_code == 200
    body = response.json()
    assert body["projectId"] == project_id
    assert body["sequence"] == 1
    assert body["budget"] == 5
    assert body["completed"] is False
    assert body["photoA"]["photoId"] in photo_ids
    assert body["photoB"]["photoId"] in photo_ids
    assert body["photoA"]["photoId"] != body["photoB"]["photoId"]
    assert body["photoA"]["imageUrl"].startswith(f"/projects/{project_id}/photos/")
    assert body["photoB"]["imageUrl"].startswith(f"/projects/{project_id}/photos/")


def test_photo_content_contract_returns_the_uploaded_jpeg(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    client = make_client(project_service)
    project_id, photo_ids = create_project_with_photos(client, jpeg_bytes, 2)

    response = client.get(f"/projects/{project_id}/photos/{photo_ids[0]}/content")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == jpeg_bytes


def test_photo_content_cannot_cross_project_boundaries(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    client = make_client(project_service)
    first_project, _ = create_project_with_photos(client, jpeg_bytes, 2)
    _, second_photo_ids = create_project_with_photos(client, jpeg_bytes, 2)

    response = client.get(
        f"/projects/{first_project}/photos/{second_photo_ids[0]}/content"
    )

    assert response.status_code == 404


def test_submit_choice_contract_records_winner_and_loser(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    client = make_client(project_service)
    project_id, _ = create_project_with_photos(client, jpeg_bytes, 3)
    pair = client.get(f"/projects/{project_id}/comparisons/next").json()

    response = client.post(
        f"/projects/{project_id}/comparisons",
        json={
            "photoAId": pair["photoA"]["photoId"],
            "photoBId": pair["photoB"]["photoId"],
            "winnerId": pair["photoA"]["photoId"],
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "projectId": project_id,
        "winnerId": pair["photoA"]["photoId"],
        "loserId": pair["photoB"]["photoId"],
        "sequence": 1,
        "completedCount": 1,
        "budget": 5,
    }


def test_invalid_winner_and_same_photo_requests_are_rejected(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    client = make_client(project_service)
    project_id, photo_ids = create_project_with_photos(client, jpeg_bytes, 3)

    invalid_winner = client.post(
        f"/projects/{project_id}/comparisons",
        json={
            "photoAId": photo_ids[0],
            "photoBId": photo_ids[1],
            "winnerId": photo_ids[2],
        },
    )
    same_photo = client.post(
        f"/projects/{project_id}/comparisons",
        json={
            "photoAId": photo_ids[0],
            "photoBId": photo_ids[0],
            "winnerId": photo_ids[0],
        },
    )

    assert invalid_winner.status_code == 422
    assert same_photo.status_code == 422


def test_reversed_duplicate_pair_returns_conflict(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    client = make_client(project_service)
    project_id, photo_ids = create_project_with_photos(client, jpeg_bytes, 2)
    first = client.post(
        f"/projects/{project_id}/comparisons",
        json={
            "photoAId": photo_ids[0],
            "photoBId": photo_ids[1],
            "winnerId": photo_ids[0],
        },
    )

    duplicate = client.post(
        f"/projects/{project_id}/comparisons",
        json={
            "photoAId": photo_ids[1],
            "photoBId": photo_ids[0],
            "winnerId": photo_ids[1],
        },
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_next_pair_reports_completion_after_five_choices(
    project_service: ProjectService, jpeg_bytes: bytes
) -> None:
    client = make_client(project_service)
    project_id, _ = create_project_with_photos(client, jpeg_bytes, 6)
    for _ in range(5):
        pair = client.get(f"/projects/{project_id}/comparisons/next").json()
        saved = client.post(
            f"/projects/{project_id}/comparisons",
            json={
                "photoAId": pair["photoA"]["photoId"],
                "photoBId": pair["photoB"]["photoId"],
                "winnerId": pair["photoA"]["photoId"],
            },
        )
        assert saved.status_code == 201

    completed = client.get(f"/projects/{project_id}/comparisons/next")

    assert completed.status_code == 200
    assert completed.json() == {
        "projectId": project_id,
        "sequence": 6,
        "budget": 5,
        "completed": True,
        "photoA": None,
        "photoB": None,
    }
