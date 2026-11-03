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

    def submit(self, project_id: str) -> str:
        with self._lock:
            current = self._states.get(project_id)
            if current in {"queued", "running"}:
                return current
            self._states[project_id] = "queued"
            self._executor.submit(self._run, project_id)
            return "queued"

    def status(self, project_id: str) -> str | None:
        with self._lock:
            return self._states.get(project_id)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=False)

    def _run(self, project_id: str) -> None:
        with self._lock:
            self._states[project_id] = "running"
        try:
            self.extractor.analyze(self.repository.list_photos(project_id))
        finally:
            with self._lock:
                self._states.pop(project_id, None)

