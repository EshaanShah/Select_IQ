"""A-10 project-linked satisfaction feedback."""

from selectiq.domain.errors import ProjectNotFoundError, ValidationError
from selectiq.domain.models import SatisfactionFeedback
from selectiq.infrastructure.project_repository import (
    FeedbackRepository,
    ProjectRepository,
    ProposalRepository,
)


class FeedbackService:
    def __init__(
        self,
        projects: ProjectRepository,
        proposals: ProposalRepository,
        feedback: FeedbackRepository,
    ) -> None:
        self.projects = projects
        self.proposals = proposals
        self.feedback = feedback

    def submit(self, project_id: str, rating: int, comment: str | None) -> SatisfactionFeedback:
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            raise ValidationError("Rating must be an integer between 1 and 5.")
        if self.projects.get(project_id) is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        if self.proposals.latest(project_id) is None:
            raise ValidationError("Generate a proposal before submitting satisfaction feedback.")
        return self.feedback.save(SatisfactionFeedback(project_id, rating, comment))

    def current(self, project_id: str) -> SatisfactionFeedback | None:
        return self.feedback.get(project_id)

