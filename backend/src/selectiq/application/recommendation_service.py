"""A-07 proposal generation: exactly K photos ranked from real project signals."""

from selectiq.application.proposal_signals import ProjectSignalProvider
from selectiq.domain.errors import ProjectNotFoundError, ProposalNotFoundError, ValidationError
from selectiq.domain.models import Project, Proposal, ProposalItem
from selectiq.infrastructure.project_repository import ProjectRepository, ProposalRepository
from selectiq.intelligence.curator import evidence_weighted, propose


class RecommendationService:
    def __init__(
        self,
        projects: ProjectRepository,
        proposals: ProposalRepository,
        signal_provider: ProjectSignalProvider,
    ) -> None:
        self.projects = projects
        self.proposals = proposals
        self.signal_provider = signal_provider

    def generate(self, project_id: str, target_count: int | None = None) -> Proposal:
        project = self._require_project(project_id)
        if target_count is None:
            target_count = project.target_count
        if target_count is None:
            raise ValidationError("Save a creative brief and target before generating a proposal.")
        bundle = self.signal_provider.collect(project)
        excluded = bundle.provenance.excluded_photo_count
        if excluded and target_count > len(bundle.signals):
            raise ValidationError(
                f"Only {len(bundle.signals)} photographs finished analysis. Lower the target or "
                f"retry analysis for the {excluded} that failed."
            )
        weights = evidence_weighted(bundle.provenance.comparisons_used)
        ranked = propose(bundle.signals, target_count, weights)
        filenames = {photo.id: photo.original_filename for photo in project.photos}
        items = [
            ProposalItem(
                photo_id=entry.photo_id,
                original_filename=filenames[entry.photo_id],
                rank=entry.rank,
                score=entry.score,
                contributions=entry.contributions,
            )
            for entry in ranked
        ]
        parameters: dict[str, object] = {
            "weights": weights.as_dict(),
            "preference_model_version": bundle.preference_model_version,
        }
        return self.proposals.create(
            project.id, target_count, bundle.provenance, parameters, items
        )

    def current(self, project_id: str) -> Proposal:
        self._require_project(project_id)
        proposal = self.proposals.latest(project_id)
        if proposal is None:
            raise ProposalNotFoundError(f"Project {project_id} has no proposal yet.")
        return proposal

    def _require_project(self, project_id: str) -> Project:
        project = self.projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        return project
