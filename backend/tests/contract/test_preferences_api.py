"""A-06 red contract tests for reading project preference scores."""

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from selectiq.api.main import create_app
from selectiq.api.routes.comparisons import comparison_service as comparison_service_dependency
from selectiq.api.routes.comparisons import preference_service as preference_service_dependency
from selectiq.api.routes.projects import project_service as project_service_dependency
from selectiq.application.comparison_service import ComparisonService
from selectiq.application.preference_service import PreferenceService
from selectiq.application.project_service import ProjectService
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.model_adapters import DeterministicVisualEncoder
from selectiq.intelligence.feature_extractor import FeatureExtractor
from selectiq.intelligence.pair_selector import DeterministicPairSelector
from selectiq.intelligence.preference_model import PairwisePreferenceModel

COLORS = ["#d64545", "#45d66b", "#4561d6"]


def make_jpeg(color: str = "#416b55") -> bytes:
    output = BytesIO()
    Image.new("RGB", (16, 12), color).save(output, format="JPEG")
    return output.getvalue()


def make_client(project_service: ProjectService) -> TestClient:
    app = create_app()
    comparisons = ComparisonService(
        repository=project_service.repository,
        pair_selector=DeterministicPairSelector(),
        comparison_budget=5,
    )
    preferences = PreferenceService(
        repository=project_service.repository, model=PairwisePreferenceModel(seed=0)
    )
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    app.dependency_overrides[comparison_service_dependency] = lambda: comparisons
    app.dependency_overrides[preference_service_dependency] = lambda: preferences
    return TestClient(app)


def analyzed_project(client: TestClient, project_service: ProjectService, tmp_path) -> str:
    project_id = client.post("/projects").json()["projectId"]
    uploaded = client.post(
        f"/projects/{project_id}/photos",
        files=[
            ("files", (f"photo-{index}.jpg", BytesIO(make_jpeg(color=color)), "image/jpeg"))
            for index, color in enumerate(COLORS)
        ],
    )
    assert uploaded.status_code == 200
    FeatureExtractor(
        project_service.repository,
        NumpyEmbeddingCache(tmp_path / "cache"),
        DeterministicVisualEncoder(dimension=8),
    ).analyze(project_service.repository.list_photos(project_id))
    return project_id


def test_preferences_contract_reports_scores_and_honest_method(
    project_service: ProjectService, tmp_path
) -> None:
    client = make_client(project_service)
    project_id = analyzed_project(client, project_service, tmp_path)
    pair = client.get(f"/projects/{project_id}/comparisons/next").json()
    winner = pair["photoB"]["photoId"]
    saved = client.post(
        f"/projects/{project_id}/comparisons",
        json={
            "photoAId": pair["photoA"]["photoId"],
            "photoBId": winner,
            "winnerId": winner,
        },
    )
    assert saved.status_code in (200, 201)

    response = client.get(f"/projects/{project_id}/preferences")

    assert response.status_code == 200
    body = response.json()
    assert body["projectId"] == project_id
    assert body["comparisonsUsed"] == 1
    assert body["method"] == "regularized_pairwise_logistic"
    assert body["modelVersion"]
    scores = {entry["photoId"]: entry["score"] for entry in body["scores"]}
    assert len(scores) == len(COLORS)
    assert scores[winner] > scores[pair["photoA"]["photoId"]]
    ordered = [entry["score"] for entry in body["scores"]]
    assert ordered == sorted(ordered, reverse=True)


def test_preferences_for_unknown_project_return_404(project_service: ProjectService) -> None:
    client = make_client(project_service)

    response = client.get("/projects/00000000-0000-0000-0000-000000000000/preferences")

    assert response.status_code == 404


def test_preferences_before_analysis_return_409(project_service: ProjectService) -> None:
    client = make_client(project_service)
    project_id = client.post("/projects").json()["projectId"]
    client.post(
        f"/projects/{project_id}/photos",
        files=[("files", ("a.jpg", BytesIO(make_jpeg()), "image/jpeg"))],
    )

    response = client.get(f"/projects/{project_id}/preferences")

    assert response.status_code == 409
