import json
import time
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from selectiq.api.main import create_app
from selectiq.api.routes.projects import analysis_service as analysis_service_dependency
from selectiq.api.routes.projects import project_service as project_service_dependency
from selectiq.application.analysis_service import AnalysisService
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.model_adapters import DeterministicVisualEncoder
from selectiq.infrastructure.reasoners import ReasonerError, ScriptedBriefReasoner
from selectiq.intelligence.brief_interpreter import BriefInterpreter
from selectiq.intelligence.feature_extractor import FeatureExtractor
from selectiq.jobs.analyze_gallery import GalleryAnalysisRunner

VALID = json.dumps(
    {
        "summary": "Favor candid warmth.",
        "positive_descriptors": ["a warm candid moment"],
        "negative_descriptors": [],
        "photo_notes": [{"label": "P01", "effect": "boost", "reason": "Natural laughter."}],
    }
)


@pytest.fixture
def api(project_service, tmp_path):
    def build(scripted):
        cache = NumpyEmbeddingCache(tmp_path / "cache")
        encoder = DeterministicVisualEncoder()
        reasoner = ScriptedBriefReasoner(scripted)
        interpreter = BriefInterpreter(project_service.repository, cache, encoder, reasoner)
        extractor = FeatureExtractor(project_service.repository, cache, encoder)
        runner = GalleryAnalysisRunner(project_service.repository, extractor, interpreter)
        service = AnalysisService(project_service.repository, runner)
        app = create_app()
        app.dependency_overrides[project_service_dependency] = lambda: project_service
        app.dependency_overrides[analysis_service_dependency] = lambda: service
        built.append(runner)
        return TestClient(app), reasoner

    built: list[GalleryAnalysisRunner] = []
    yield build
    for runner in built:
        runner.shutdown()


def prepared_project(client: TestClient, jpeg_bytes: bytes) -> tuple[str, str]:
    project_id = client.post("/projects").json()["projectId"]
    uploaded = client.post(
        f"/projects/{project_id}/photos",
        files=[("files", ("laugh.jpg", BytesIO(jpeg_bytes), "image/jpeg"))],
    )
    client.post(f"/projects/{project_id}/brief", json={"prompt": "Candid warmth.", "target": 1})
    return project_id, uploaded.json()["accepted"][0]["photoId"]


def wait_for_interpretation(client: TestClient, project_id: str) -> dict:
    for _ in range(300):
        body = client.get(f"/projects/{project_id}/interpretation").json()
        if body["status"] in {"completed", "failed"}:
            return body
        time.sleep(0.01)
    raise AssertionError(f"Interpretation did not finish: {body}")


def test_analysis_runs_interpretation_and_exposes_auditable_guidance(api, jpeg_bytes) -> None:
    client, reasoner = api([VALID])
    project_id, photo_id = prepared_project(client, jpeg_bytes)
    before = client.get(f"/projects/{project_id}/interpretation")
    assert before.status_code == 200 and before.json()["status"] == "not_started"

    assert client.post(f"/projects/{project_id}/analyze").status_code == 202
    body = wait_for_interpretation(client, project_id)

    assert body["status"] == "completed"
    assert body["provider"] == "scripted"
    assert body["model"] == "scripted-test"
    assert body["summary"] == "Favor candid warmth."
    assert body["positiveDescriptors"] == ["a warm candid moment"]
    assert body["photoNotes"] == [
        {
            "photoId": photo_id,
            "originalFilename": "laugh.jpg",
            "effect": "boost",
            "reason": "Natural laughter.",
        }
    ]
    assert body["errorCode"] is None
    assert body["rankingBasis"] == "guided"
    entry = body["ranking"][0]
    assert entry["photoId"] == photo_id and entry["rank"] == 1
    assert entry["guidedScore"] is not None and entry["briefRelevance"] is not None
    assert "Natural laughter." in entry["explanation"]
    assert len(reasoner.requests) == 1

    assert client.post(f"/projects/{project_id}/analyze").status_code == 200
    time.sleep(0.05)
    assert len(reasoner.requests) == 1


def test_failed_interpretation_is_labeled_and_retry_succeeds(api, jpeg_bytes) -> None:
    client, reasoner = api([ReasonerError("rate_limited", "Groq is busy."), VALID])
    project_id, _ = prepared_project(client, jpeg_bytes)
    client.post(f"/projects/{project_id}/analyze")

    failed = wait_for_interpretation(client, project_id)
    assert failed["status"] == "failed"
    assert failed["errorCode"] == "rate_limited"
    assert failed["errorMessage"] == "Groq is busy."
    assert failed["summary"] is None
    assert failed["rankingBasis"] == "brief_relevance"
    assert failed["ranking"][0]["guidedScore"] is None

    retried = client.post(f"/projects/{project_id}/interpretation")
    assert retried.status_code == 202
    assert wait_for_interpretation(client, project_id)["status"] == "completed"
    assert len(reasoner.requests) == 2


def test_interpretation_requires_completed_analysis(api, jpeg_bytes) -> None:
    client, _ = api([VALID])
    assert client.get("/projects/not-a-project/interpretation").status_code == 404
    assert client.post("/projects/not-a-project/interpretation").status_code == 404
    project_id, _ = prepared_project(client, jpeg_bytes)

    response = client.post(f"/projects/{project_id}/interpretation")

    assert response.status_code == 409
    assert "analy" in response.json()["detail"].lower()
