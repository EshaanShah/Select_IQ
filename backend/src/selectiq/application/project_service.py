from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from selectiq.domain.errors import ImportValidationError, ProjectNotFoundError, ValidationError
from selectiq.domain.models import ImportFailure, Photograph, Project
from selectiq.infrastructure.image_store import ImageStore
from selectiq.infrastructure.project_repository import ProjectRepository


@dataclass(frozen=True, slots=True)
class PhotoUpload:
    filename: str
    stream: BinaryIO


@dataclass(frozen=True, slots=True)
class RejectedPhoto:
    filename: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ImportResult:
    accepted: list[Photograph]
    rejected: list[RejectedPhoto]
    accepted_count: int


class ProjectService:
    def __init__(
        self,
        repository: ProjectRepository,
        image_store: ImageStore,
        max_gallery_size: int = 30,
    ) -> None:
        self.repository = repository
        self.image_store = image_store
        self.max_gallery_size = max_gallery_size

    def create_project(self) -> Project:
        project = Project(id=str(uuid4()))
        self.repository.save(project)
        return project

    def get_project(self, project_id: str) -> Project:
        return self._require_project(project_id)

    def set_prompt_and_target(self, project_id: str, prompt: str, target: int) -> Project:
        project = self._require_project(project_id)
        if not prompt.strip():
            raise ValidationError("The prompt cannot be blank.")
        if isinstance(target, bool) or not isinstance(target, int):
            raise ValidationError("The target must be an integer.")
        if target < 1:
            raise ValidationError("The target must be positive and at least 1.")
        accepted_count = len(project.photos)
        if accepted_count == 0:
            raise ValidationError("Upload at least one accepted photo before setting a target.")
        if target > accepted_count:
            raise ValidationError(
                f"The target cannot exceed the {accepted_count} accepted photos."
            )
        if not self.repository.save_prompt_and_target(project_id, prompt, target):
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        return self._require_project(project_id)

    def import_photos(self, project_id: str, uploads: list[PhotoUpload]) -> ImportResult:
        self._require_project(project_id)
        accepted: list[Photograph] = []
        rejected: list[RejectedPhoto] = []

        for upload in uploads:
            photo_id = str(uuid4())
            final_path: Path | None = None
            try:
                staged = self.image_store.stage_upload(project_id, upload.filename, upload.stream)
                final_path = self.image_store.finalize(project_id, photo_id, staged)
                photo = Photograph(
                    id=photo_id,
                    project_id=project_id,
                    original_filename=upload.filename,
                    working_path=final_path,
                    content_hash=staged.content_hash,
                    width=staged.width,
                    height=staged.height,
                    byte_size=staged.byte_size,
                )
                if not self.repository.add_photo_if_capacity(photo, self.max_gallery_size):
                    self.image_store.discard(final_path)
                    final_path = None
                    self._reject(
                        project_id,
                        rejected,
                        upload.filename,
                        "gallery_limit_reached",
                        f"This project already contains the maximum of {self.max_gallery_size} photographs.",
                    )
                    continue
                accepted.append(photo)
            except ImportValidationError as error:
                self._reject(project_id, rejected, upload.filename, error.code, str(error))
            except Exception:
                if final_path is not None:
                    self.image_store.discard(final_path)
                raise

        return ImportResult(
            accepted=accepted,
            rejected=rejected,
            accepted_count=self.repository.accepted_count(project_id),
        )

    def status(self, project_id: str) -> tuple[Project, list[ImportFailure]]:
        project = self._require_project(project_id)
        return project, self.repository.import_failures(project_id)

    def _require_project(self, project_id: str) -> Project:
        project = self.repository.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        return project

    def _reject(
        self,
        project_id: str,
        rejected: list[RejectedPhoto],
        filename: str,
        code: str,
        message: str,
    ) -> None:
        failure = ImportFailure(filename=filename, code=code, message=message)
        self.repository.record_import_failure(project_id, failure)
        rejected.append(RejectedPhoto(filename=filename, code=code, message=message))
