from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/feedback", tags=["feedback"])

