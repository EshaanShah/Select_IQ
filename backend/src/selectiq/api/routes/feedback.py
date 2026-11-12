from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from selectiq.api.dependencies import get_feedback_service
from selectiq.application.feedback_service import FeedbackService
from selectiq.domain.errors import ProjectNotFoundError, ValidationError

router = APIRouter(prefix="/projects/{project_id}/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: StrictInt = Field(ge=1, le=5)
    comment: str | None = None


class FeedbackResponse(BaseModel):
    projectId: str
    rating: int
    comment: str | None
    createdAt: datetime | None


def feedback_service() -> FeedbackService:
    return get_feedback_service()


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    project_id: str,
    request: FeedbackRequest,
    service: Annotated[FeedbackService, Depends(feedback_service)],
) -> FeedbackResponse:
    try:
        saved = service.submit(project_id, request.rating, request.comment)
    except ProjectNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except ValidationError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    return FeedbackResponse(
        projectId=saved.project_id,
        rating=saved.rating,
        comment=saved.comment,
        createdAt=saved.created_at,
    )

