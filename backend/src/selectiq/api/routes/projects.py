import hashlib
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, StrictInt

from selectiq.api.dependencies import get_analysis_service, get_project_service
from selectiq.application.analysis_service import AnalysisService
from selectiq.application.project_service import PhotoUpload, ProjectService
from selectiq.domain.enums import ProcessingState
from selectiq.domain.errors import PhotoNotFoundError, ProjectNotFoundError, ValidationError

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


class ProjectPhoto(AcceptedPhoto):
    thumbnailUrl: str
    analysisErrorCode: str | None = None
    analysisErrorMessage: str | None = None


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
    photos: list[ProjectPhoto]
    failures: list[ImportFailureResponse]
    prompt: str | None
    target: int | None
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


class PhotoNoteResponse(CamelModel):
    photoId: str
    originalFilename: str
    effect: str
    reason: str


class RankingEntryResponse(CamelModel):
    photoId: str
    originalFilename: str
    rank: int
    guidedScore: float | None
    briefRelevance: float | None
    explanation: str | None


class InterpretationResponse(CamelModel):
    projectId: str
    status: str
    provider: str | None = None
    model: str | None = None
    summary: str | None = None
    positiveDescriptors: list[str] = []
    negativeDescriptors: list[str] = []
    photoNotes: list[PhotoNoteResponse] = []
    errorCode: str | None = None
    errorMessage: str | None = None
    createdAt: datetime | None = None
    durationMs: int | None = None
    rankingBasis: str
    ranking: list[RankingEntryResponse]


class InterpretationStarted(CamelModel):
    projectId: str
    status: str


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


@router.get("/{project_id}/photos/{photo_id}/content", response_class=FileResponse)
def photo_content(
    project_id: str,
    photo_id: str,
    service: Annotated[ProjectService, Depends(project_service)],
) -> FileResponse:
    try:
        project = service.get_project(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    photo = next((item for item in project.photos if item.id == photo_id), None)
    if photo is None or not photo.working_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo was not found.")
    return FileResponse(photo.working_path, media_type="image/jpeg")


@router.get("/{project_id}/photos/{photo_id}/thumbnail", response_class=FileResponse)
def photo_thumbnail(
    project_id: str,
    photo_id: str,
    service: Annotated[ProjectService, Depends(project_service)],
) -> FileResponse:
    try:
        path = service.thumbnail(project_id, photo_id)
    except PhotoNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return FileResponse(
        path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"}
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
    completed = [photo for photo in project.photos if photo.state is ProcessingState.COMPLETED]
    failed = [photo for photo in project.photos if photo.state is ProcessingState.FAILED]
    processing = [photo for photo in project.photos if photo.state is ProcessingState.PROCESSING]
    prompt_hash = (
        hashlib.sha256(project.brief.original_text.encode("utf-8")).hexdigest()
        if project.brief is not None
        else None
    )
    prompt_current = bool(prompt_hash) and all(
        (feature := service.repository.get_feature(photo.id)) is not None
        and feature.prompt_hash == prompt_hash
        and feature.brief_relevance is not None
        for photo in completed
    )
    if processing:
        analysis_status = "running"
    elif project.photos and len(completed) == len(project.photos) and prompt_current:
        analysis_status = "completed"
    elif completed and failed:
        analysis_status = "partial_failure"
    elif project.photos and len(failed) == len(project.photos):
        analysis_status = "failed"
    else:
        analysis_status = "idle"
    feature = next((service.repository.get_feature(photo.id) for photo in completed), None)
    return ProjectStatus(
        projectId=project_id,
        acceptedCount=len(project.photos),
        remainingCapacity=max(service.max_gallery_size - len(project.photos), 0),
        photos=[
            ProjectPhoto(
                photoId=photo.id,
                originalFilename=photo.original_filename,
                width=photo.width,
                height=photo.height,
                byteSize=photo.byte_size,
                state=photo.state.value,
                thumbnailUrl=f"/projects/{project_id}/photos/{photo.id}/thumbnail",
                analysisErrorCode=photo.analysis_error_code,
                analysisErrorMessage=photo.analysis_error_message,
            )
            for photo in project.photos
        ],
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
        analysisStatus=analysis_status,
        analysisTotal=len(project.photos),
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


@router.get("/{project_id}/interpretation", response_model=InterpretationResponse)
def get_interpretation(
    project_id: str, service: Annotated[AnalysisService, Depends(analysis_service)]
) -> InterpretationResponse:
    try:
        view = service.interpretation(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValidationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    item = view.interpretation
    filename = view.filenames.get
    return InterpretationResponse(
        projectId=project_id,
        status=view.status,
        provider=item.provider if item else None,
        model=item.model_name if item else None,
        summary=item.summary if item else None,
        positiveDescriptors=list(item.positive_descriptors) if item else [],
        negativeDescriptors=list(item.negative_descriptors) if item else [],
        photoNotes=[
            PhotoNoteResponse(
                photoId=note.photo_id,
                originalFilename=filename(note.photo_id, ""),
                effect=note.effect,
                reason=note.reason,
            )
            for note in (item.photo_notes if item else ())
        ],
        errorCode=item.error_code if item else None,
        errorMessage=item.error_message if item else None,
        createdAt=item.created_at if item else None,
        durationMs=item.duration_ms if item else None,
        rankingBasis=view.ranking.basis,
        ranking=[
            RankingEntryResponse(
                photoId=entry.photo_id,
                originalFilename=filename(entry.photo_id, ""),
                rank=entry.rank,
                guidedScore=entry.guided_score,
                briefRelevance=entry.brief_relevance,
                explanation=entry.explanation,
            )
            for entry in view.ranking.entries
        ],
    )


@router.post(
    "/{project_id}/interpretation",
    response_model=InterpretationStarted,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_interpretation(
    project_id: str, service: Annotated[AnalysisService, Depends(analysis_service)]
) -> InterpretationStarted:
    try:
        started = service.start_interpretation(project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValidationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return InterpretationStarted(projectId=project_id, status=started)
