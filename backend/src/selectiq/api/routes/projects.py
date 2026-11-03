from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, StrictInt

from selectiq.api.dependencies import get_project_service
from selectiq.application.project_service import PhotoUpload, ProjectService
from selectiq.domain.errors import ProjectNotFoundError, ValidationError

router = APIRouter(prefix="/projects", tags=["projects"])


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ProjectCreated(CamelModel):
    projectId: str
    acceptedCount: int


class AcceptedPhoto(CamelModel):
    photoId: str
    originalFilename: str
    width: int
    height: int
    byteSize: int
    state: str


class RejectedPhotoResponse(CamelModel):
    filename: str
    code: str
    message: str


class ImportResponse(CamelModel):
    accepted: list[AcceptedPhoto]
    rejected: list[RejectedPhotoResponse]
    batchAcceptedCount: int
    batchRejectedCount: int
    acceptedCount: int


class ImportFailureResponse(RejectedPhotoResponse):
    createdAt: datetime | None = None


class ProjectStatus(CamelModel):
    projectId: str
    acceptedCount: int
    remainingCapacity: int
    failures: list[ImportFailureResponse]
    prompt: str | None
    target: int | None


class PromptTargetRequest(CamelModel):
    prompt: str
    target: StrictInt


class PromptTargetResponse(CamelModel):
    projectId: str
    prompt: str
    target: int
    acceptedCount: int


def project_service() -> ProjectService:
    return get_project_service()


@router.post("", response_model=ProjectCreated, status_code=status.HTTP_201_CREATED)
def create_project(service: Annotated[ProjectService, Depends(project_service)]) -> ProjectCreated:
    project = service.create_project()
    return ProjectCreated(projectId=project.id, acceptedCount=0)


@router.post("/{project_id}/photos", response_model=ImportResponse)
def upload_photos(
    project_id: str,
    files: Annotated[list[UploadFile], File(...)],
    service: Annotated[ProjectService, Depends(project_service)],
) -> ImportResponse:
    try:
        result = service.import_photos(
            project_id,
            [PhotoUpload(filename=file.filename or "upload", stream=file.file) for file in files],
        )
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    accepted = [
        AcceptedPhoto(
            photoId=photo.id,
            originalFilename=photo.original_filename,
            width=photo.width,
            height=photo.height,
            byteSize=photo.byte_size,
            state=photo.state.value,
        )
        for photo in result.accepted
    ]
    rejected = [
        RejectedPhotoResponse(filename=item.filename, code=item.code, message=item.message)
        for item in result.rejected
    ]
    return ImportResponse(
        accepted=accepted,
        rejected=rejected,
        batchAcceptedCount=len(accepted),
        batchRejectedCount=len(rejected),
        acceptedCount=result.accepted_count,
    )


@router.post("/{project_id}/brief", response_model=PromptTargetResponse)
def save_prompt_and_target(
    project_id: str,
    request: PromptTargetRequest,
    service: Annotated[ProjectService, Depends(project_service)],
) -> PromptTargetResponse:
    try:
        project = service.set_prompt_and_target(project_id, request.prompt, request.target)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    assert project.brief is not None and project.target_count is not None
    return PromptTargetResponse(
        projectId=project.id,
        prompt=project.brief.original_text,
        target=project.target_count,
        acceptedCount=len(project.photos),
    )


@router.get("/{project_id}/status", response_model=ProjectStatus)
def get_status(
    project_id: str, service: Annotated[ProjectService, Depends(project_service)]
) -> ProjectStatus:
    try:
        project, failures = service.status(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return ProjectStatus(
        projectId=project_id,
        acceptedCount=len(project.photos),
        remainingCapacity=max(service.max_gallery_size - len(project.photos), 0),
        prompt=project.brief.original_text if project.brief is not None else None,
        target=project.target_count,
        failures=[
            ImportFailureResponse(
                filename=failure.filename,
                code=failure.code,
                message=failure.message,
                createdAt=failure.created_at,
            )
            for failure in failures
        ],
    )
