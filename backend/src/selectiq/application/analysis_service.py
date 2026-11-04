from dataclasses import dataclass

from selectiq.domain.enums import ProcessingState
from selectiq.domain.errors import ProjectNotFoundError, ValidationError
from selectiq.infrastructure.project_repository import ProjectRepository
from selectiq.jobs.analyze_gallery import GalleryAnalysisRunner


@dataclass(frozen=True, slots=True)
class AnalysisFailure:
    photo_id: str
    original_filename: str
    code: str
    message: str


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

    def score_prompt(self, project_id: str, prompt: str) -> dict[str, float]:
        project = self.repository.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        photos = self.repository.list_photos(project_id)
        if not photos or not all(self.runner.extractor.is_current(photo) for photo in photos):
            raise ValidationError("Complete image analysis before scoring a creative brief.")
        return self.runner.extractor.score_prompt(project_id, prompt)
