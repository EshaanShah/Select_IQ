from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from selectiq.api.dependencies import get_comparison_service
from selectiq.application.comparison_service import ComparisonService
from selectiq.domain.errors import (
    DuplicateComparisonError,
    ProjectNotFoundError,
    ValidationError,
)

router = APIRouter(prefix="/projects/{project_id}/comparisons", tags=["comparisons"])


class ComparisonPhotoResponse(BaseModel):
    photoId: str
    originalFilename: str
    imageUrl: str


class NextComparisonResponse(BaseModel):
    projectId: str
    sequence: int
    budget: int
    completed: bool
    photoA: ComparisonPhotoResponse | None
    photoB: ComparisonPhotoResponse | None


class ComparisonChoiceRequest(BaseModel):
    photoAId: str
    photoBId: str
    winnerId: str


class ComparisonChoiceResponse(BaseModel):
    projectId: str
    winnerId: str
    loserId: str
    sequence: int
    completedCount: int
    budget: int


def comparison_service() -> ComparisonService:
    return get_comparison_service()


@router.get("/next", response_model=NextComparisonResponse)
def next_comparison(
    project_id: str, service: Annotated[ComparisonService, Depends(comparison_service)]
) -> NextComparisonResponse:
    try:
        pair = service.next_pair(project_id)
        project = service.repository.get(project_id)
        assert project is not None
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    if pair is None:
        completed_count = len(service.choices(project_id))
        return NextComparisonResponse(
            projectId=project_id,
            sequence=completed_count + 1,
            budget=service.comparison_budget,
            completed=True,
            photoA=None,
            photoB=None,
        )

    photos = {photo.id: photo for photo in project.photos}

    def response_photo(photo_id: str) -> ComparisonPhotoResponse:
        photo = photos[photo_id]
        return ComparisonPhotoResponse(
            photoId=photo.id,
            originalFilename=photo.original_filename,
            imageUrl=f"/projects/{project_id}/photos/{photo.id}/content",
        )

    return NextComparisonResponse(
        projectId=project_id,
        sequence=pair.sequence,
        budget=pair.budget,
        completed=False,
        photoA=response_photo(pair.photo_a_id),
        photoB=response_photo(pair.photo_b_id),
    )


@router.post("", response_model=ComparisonChoiceResponse, status_code=status.HTTP_201_CREATED)
def save_comparison(
    project_id: str,
    request: ComparisonChoiceRequest,
    service: Annotated[ComparisonService, Depends(comparison_service)],
) -> ComparisonChoiceResponse:
    try:
        choice = service.record_choice(
            project_id, request.photoAId, request.photoBId, request.winnerId
        )
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except DuplicateComparisonError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    return ComparisonChoiceResponse(
        projectId=project_id,
        winnerId=choice.winner_id,
        loserId=choice.loser_id,
        sequence=choice.sequence,
        completedCount=choice.sequence,
        budget=service.comparison_budget,
    )

