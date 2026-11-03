import time
from io import BytesIO

from fastapi.testclient import TestClient

from selectiq.api.main import create_app
from selectiq.api.routes.projects import analysis_service as analysis_service_dependency
from selectiq.api.routes.projects import project_service as project_service_dependency
from selectiq.application.analysis_service import AnalysisService
from selectiq.application.project_service import ProjectService
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.model_adapters import DeterministicVisualEncoder
from selectiq.intelligence.feature_extractor import FeatureExtractor
from selectiq.jobs.analyze_gallery import GalleryAnalysisRunner


def test_analysis_endpoint_reports_completion_and_cache_reuse(
    project_service: ProjectService, jpeg_bytes: bytes, tmp_path
) -> None:
    extractor = FeatureExtractor(
        project_service.repository,
        NumpyEmbeddingCache(tmp_path / "cache"),
        DeterministicVisualEncoder(),
    )
    runner = GalleryAnalysisRunner(project_service.repository, extractor)
    service = AnalysisService(project_service.repository, runner)
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    app.dependency_overrides[analysis_service_dependency] = lambda: service
    client = TestClient(app)
    project_id = client.post("/projects").json()["projectId"]
    client.post(
        f"/projects/{project_id}/photos",
        files=[("files", ("photo.jpg", BytesIO(jpeg_bytes), "image/jpeg"))],
    )

    started = client.post(f"/projects/{project_id}/analyze")
    assert started.status_code == 202
    for _ in range(100):
        status = client.get(f"/projects/{project_id}/status").json()
        if status["analysisStatus"] == "completed":
            break
        time.sleep(0.01)
    assert status["analysisCompleted"] == 1
    assert status["analysisFailed"] == 0
    assert status["analysisModel"] == "deterministic-test"
    assert client.post(f"/projects/{project_id}/analyze").status_code == 200
    runner.shutdown()


def test_analysis_requires_a_known_nonempty_project(project_service: ProjectService, tmp_path) -> None:
    runner = GalleryAnalysisRunner(
        project_service.repository,
        FeatureExtractor(
            project_service.repository,
            NumpyEmbeddingCache(tmp_path / "cache"),
            DeterministicVisualEncoder(),
        ),
    )
    service = AnalysisService(project_service.repository, runner)
    app = create_app()
    app.dependency_overrides[project_service_dependency] = lambda: project_service
    app.dependency_overrides[analysis_service_dependency] = lambda: service
    client = TestClient(app)

    assert client.post("/projects/not-a-project/analyze").status_code == 404
    project_id = client.post("/projects").json()["projectId"]
    assert client.post(f"/projects/{project_id}/analyze").status_code == 409
    runner.shutdown()
