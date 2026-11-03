from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict

from selectiq.api.dependencies import get_analysis_service, get_project_service
from selectiq.application.analysis_service import AnalysisService
from selectiq.application.project_service import PhotoUpload, ProjectService
from selectiq.domain.enums import ProcessingState
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
    analysisStatus: str
    analysisTotal: int
    analysisCompleted: int
    analysisFailed: int
    analysisFailures: list["AnalysisFailureResponse"]
    analysisModel: str | None = None
    analysisCheckpoint: str | None = None
    embeddingDimension: int | None = None


class AnalysisFailureResponse(CamelModel):
    photoId: str
    originalFilename: str
    code: str
    message: str


class AnalysisStarted(CamelModel):
    projectId: str
    analysisStatus: str


def project_service() -> ProjectService:
    return get_project_service()


def analysis_service() -> AnalysisService:
    return get_analysis_service()


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


@router.get("/{project_id}/status", response_model=ProjectStatus)
def get_status(
    project_id: str, service: Annotated[ProjectService, Depends(project_service)]
) -> ProjectStatus:
    try:
        accepted_count, failures = service.status(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    photos = service.repository.list_photos(project_id)
    completed = [photo for photo in photos if photo.state is ProcessingState.COMPLETED]
    failed = [photo for photo in photos if photo.state is ProcessingState.FAILED]
    processing = [photo for photo in photos if photo.state is ProcessingState.PROCESSING]
    if processing:
        analysis_status = "running"
    elif photos and len(completed) == len(photos):
        analysis_status = "completed"
    elif completed and failed:
        analysis_status = "partial_failure"
    elif photos and len(failed) == len(photos):
        analysis_status = "failed"
    else:
        analysis_status = "idle"
    feature = next((service.repository.get_feature(photo.id) for photo in completed), None)
    return ProjectStatus(
        projectId=project_id,
        acceptedCount=accepted_count,
        remainingCapacity=max(service.max_gallery_size - accepted_count, 0),
        failures=[
            ImportFailureResponse(
                filename=failure.filename,
                code=failure.code,
                message=failure.message,
                createdAt=failure.created_at,
            )
            for failure in failures
        ],
        analysisStatus=analysis_status,
        analysisTotal=len(photos),
        analysisCompleted=len(completed),
        analysisFailed=len(failed),
        analysisFailures=[
            AnalysisFailureResponse(
                photoId=photo.id,
                originalFilename=photo.original_filename,
                code=photo.analysis_error_code or "analysis_failed",
                message=photo.analysis_error_message or "Analysis failed.",
            )
            for photo in failed
        ],
        analysisModel=feature.model_name if feature else None,
        analysisCheckpoint=feature.checkpoint if feature else None,
        embeddingDimension=feature.embedding_dimension if feature else None,
    )


@router.post("/{project_id}/analyze", response_model=AnalysisStarted)
def analyze_project(
    project_id: str,
    service: Annotated[AnalysisService, Depends(analysis_service)],
    response: Response,
) -> AnalysisStarted:
    try:
        analysis_status, queued = service.start(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValidationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    response.status_code = status.HTTP_202_ACCEPTED if queued else status.HTTP_200_OK
    return AnalysisStarted(projectId=project_id, analysisStatus=analysis_status)
