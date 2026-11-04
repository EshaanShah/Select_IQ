from dataclasses import dataclass

from selectiq.domain.enums import ProcessingState
from selectiq.domain.errors import ProjectNotFoundError, ValidationError
from selectiq.domain.models import BriefInterpretation
from selectiq.infrastructure.project_repository import ProjectRepository
from selectiq.intelligence.brief_interpreter import Ranking, prompt_hash
from selectiq.jobs.analyze_gallery import GalleryAnalysisRunner


@dataclass(frozen=True, slots=True)
class AnalysisFailure:
    photo_id: str
    original_filename: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class InterpretationView:
    status: str  # not_started, running, completed, failed
    interpretation: BriefInterpretation | None
    ranking: Ranking
    filenames: dict[str, str]


@dataclass(frozen=True, slots=True)
class AnalysisStatus:
    status: str
    total: int
    completed: int
    failed: int
    failures: tuple[AnalysisFailure, ...]
    model_name: str | None = None
    checkpoint: str | None = None
    embedding_dimension: int | None = None


class AnalysisService:
    def __init__(self, repository: ProjectRepository, runner: GalleryAnalysisRunner):
        self.repository = repository
        self.runner = runner

    def start(self, project_id: str) -> tuple[str, bool]:
        project = self.repository.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        photos = self.repository.list_photos(project_id)
        if not photos:
            raise ValidationError("Upload at least one photograph before starting analysis.")
        if project.brief is None:
            raise ValidationError("Save a creative brief before starting analysis.")
        prompt = project.brief.original_text
        if all(
            self.runner.extractor.is_current(photo)
            and self.runner.extractor.is_prompt_current(photo, prompt)
            for photo in photos
        ):
            if self.runner.interpreter is not None:
                latest = self.repository.latest_interpretation(project_id)
                # Galleries analyzed before A-04, or whose brief changed, still need guidance.
                # A failed attempt for this brief waits for an explicit retry.
                if latest is None or latest.prompt_hash != prompt_hash(prompt):
                    self.runner.submit_interpretation(project_id)
            return "completed", False
        return self.runner.submit(project_id, prompt), True

    def status(self, project_id: str) -> AnalysisStatus:
        project = self.repository.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        photos = self.repository.list_photos(project_id)
        completed = [photo for photo in photos if photo.state is ProcessingState.COMPLETED]
        failed = [photo for photo in photos if photo.state is ProcessingState.FAILED]
        runtime = self.runner.status(project_id)
        if runtime in {"queued", "running"}:
            status = runtime
        elif not photos or all(photo.state is ProcessingState.PENDING for photo in photos):
            status = "idle"
        elif len(completed) == len(photos):
            status = "completed"
        elif failed and completed:
            status = "partial_failure"
        elif len(failed) == len(photos):
            status = "failed"
        else:
            status = "idle"

        first_feature = next(
            (self.repository.get_feature(photo.id) for photo in completed), None
        )
        return AnalysisStatus(
            status=status,
            total=len(photos),
            completed=len(completed),
            failed=len(failed),
            failures=tuple(
                AnalysisFailure(
                    photo_id=photo.id,
                    original_filename=photo.original_filename,
                    code=photo.analysis_error_code or "analysis_failed",
                    message=photo.analysis_error_message or "Analysis failed.",
                )
                for photo in failed
            ),
            model_name=first_feature.model_name if first_feature else None,
            checkpoint=first_feature.checkpoint if first_feature else None,
            embedding_dimension=first_feature.embedding_dimension if first_feature else None,
        )

    def interpretation(self, project_id: str) -> InterpretationView:
        project = self.repository.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        interpreter = self.runner.interpreter
        if interpreter is None:
            raise ValidationError("Brief interpretation is not configured.")
        latest = self.repository.latest_interpretation(project_id)
        current_hash = prompt_hash(project.brief.original_text) if project.brief else None
        if latest is not None and latest.prompt_hash != current_hash:
            latest = None
        if self.runner.is_active(project_id):
            status = "running"
        elif latest is not None:
            status = latest.status
        else:
            status = "not_started"
        return InterpretationView(
            status=status,
            interpretation=latest,
            ranking=interpreter.ranking(project_id),
            filenames={photo.id: photo.original_filename for photo in project.photos},
        )

    def start_interpretation(self, project_id: str) -> str:
        project = self.repository.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        if self.runner.interpreter is None:
            raise ValidationError("Brief interpretation is not configured.")
        if project.brief is None:
            raise ValidationError("Save a creative brief before interpreting it.")
        if self.runner.is_active(project_id):
            return "running"
        analyzed = self.runner.interpreter.analyzed_photos(project_id)
        if not analyzed or not all(
            self.runner.extractor.is_prompt_current(photo, project.brief.original_text)
            for photo in analyzed
        ):
            raise ValidationError("Analyze the gallery before interpreting the brief.")
        return self.runner.submit_interpretation(project_id)

    def score_prompt(self, project_id: str, prompt: str) -> dict[str, float]:
        project = self.repository.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        photos = self.repository.list_photos(project_id)
        if not photos or not all(self.runner.extractor.is_current(photo) for photo in photos):
            raise ValidationError("Complete image analysis before scoring a creative brief.")
        return self.runner.extractor.score_prompt(project_id, prompt)
