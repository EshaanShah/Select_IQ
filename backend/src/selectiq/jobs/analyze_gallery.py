"""Single-worker, in-process gallery analysis runner."""

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from selectiq.infrastructure.project_repository import ProjectRepository
from selectiq.intelligence.feature_extractor import FeatureExtractor


class GalleryAnalysisRunner:
    def __init__(self, repository: ProjectRepository, extractor: FeatureExtractor):
        self.repository = repository
        self.extractor = extractor
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="selectiq-analysis")
        self._states: dict[str, str] = {}
        self._lock = Lock()

    def submit(self, project_id: str, prompt: str) -> str:
        with self._lock:
            current = self._states.get(project_id)
            if current in {"queued", "running"}:
                return current
            self._states[project_id] = "queued"
            self._executor.submit(self._run, project_id, prompt)
            return "queued"

    def status(self, project_id: str) -> str | None:
        with self._lock:
            return self._states.get(project_id)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=False)

    def _run(self, project_id: str, prompt: str) -> None:
        with self._lock:
            self._states[project_id] = "running"
        try:
            result = self.extractor.analyze(self.repository.list_photos(project_id))
            if result.completed:
                try:
                    scores = self.extractor.score_prompt(project_id, prompt)
                    missing = set(result.completed) - scores.keys()
                    for photo_id in missing:
                        self.repository.mark_photo_failed(
                            photo_id,
                            "prompt_relevance_failed",
                            "The prompt could not be compared with this photograph.",
                        )
                except Exception as error:  # noqa: BLE001 - surface provider text failures
                    for photo_id in result.completed:
                        self.repository.mark_photo_failed(
                            photo_id,
                            "prompt_inference_failed",
                            str(error) or "Prompt inference failed.",
                        )
        finally:
            with self._lock:
                self._states.pop(project_id, None)

