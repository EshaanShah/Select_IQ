from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, StrictInt

from selectiq.api.dependencies import get_recommendation_service
from selectiq.application.recommendation_service import RecommendationService
from selectiq.domain.errors import ProjectNotFoundError, ProposalNotFoundError, ValidationError
from selectiq.domain.models import Proposal

router = APIRouter(prefix="/projects/{project_id}/recommendations", tags=["recommendations"])


class GenerateProposalRequest(BaseModel):
    targetCount: StrictInt | None = None


class Contributions(BaseModel):
    promptRelevance: float
    aiGuidance: float
    preference: float


class RecommendationResponse(BaseModel):
    photoId: str
    originalFilename: str
    rank: int
    score: float
    contributions: Contributions


class ProvenanceResponse(BaseModel):
    kind: str
    label: str
    embeddingModel: str
    embeddingsGenuine: bool
    guidanceModel: str | None
    guidanceStatus: str
    guidanceGenuine: bool
    comparisonsUsed: int
    preferenceMethod: str
    excludedPhotoCount: int


class ProposalResponse(BaseModel):
    proposalId: str
    projectId: str
    version: int
    targetCount: int
    selectedCount: int
    isGenuineAi: bool
    provenance: ProvenanceResponse
    parameters: dict[str, object]
    createdAt: datetime | None
    recommendations: list[RecommendationResponse]


def recommendation_service() -> RecommendationService:
    return get_recommendation_service()


Service = Annotated[RecommendationService, Depends(recommendation_service)]


@router.post("", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
def generate_proposal(
    project_id: str, service: Service, request: GenerateProposalRequest | None = None
) -> ProposalResponse:
    target_count = request.targetCount if request is not None else None
    try:
        return to_response(service.generate(project_id, target_count))
    except ProjectNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except ValidationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.get("", response_model=ProposalResponse)
def read_proposal(project_id: str, service: Service) -> ProposalResponse:
    try:
        return to_response(service.current(project_id))
    except (ProjectNotFoundError, ProposalNotFoundError) as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error


def to_response(proposal: Proposal) -> ProposalResponse:
    provenance = proposal.provenance
    return ProposalResponse(
        proposalId=proposal.id,
        projectId=proposal.project_id,
        version=proposal.version,
        targetCount=proposal.target_count,
        selectedCount=len(proposal.items),
        isGenuineAi=provenance.is_genuine_ai,
        provenance=ProvenanceResponse(
            kind=provenance.kind,
            label=provenance.label,
            embeddingModel=provenance.embedding_model,
            embeddingsGenuine=provenance.embeddings_genuine,
            guidanceModel=provenance.guidance_model,
            guidanceStatus=provenance.guidance_status,
            guidanceGenuine=provenance.guidance_genuine,
            comparisonsUsed=provenance.comparisons_used,
            preferenceMethod=provenance.preference_method,
            excludedPhotoCount=provenance.excluded_photo_count,
        ),
        parameters=proposal.parameters,
        createdAt=proposal.created_at,
        recommendations=[
            RecommendationResponse(
                photoId=item.photo_id,
                originalFilename=item.original_filename,
                rank=item.rank,
                score=item.score,
                contributions=Contributions(
                    promptRelevance=item.contributions["prompt_relevance"],
                    aiGuidance=item.contributions["ai_guidance"],
                    preference=item.contributions["preference"],
                ),
            )
            for item in proposal.items
        ],
    )
