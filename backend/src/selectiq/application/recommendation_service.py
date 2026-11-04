"""A-07 proposal generation and A-08 review, removal, and export."""

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from selectiq.application.proposal_signals import ProjectSignalProvider
from selectiq.domain.errors import (
    PhotoNotInProposalError,
    ProjectNotFoundError,
    ProposalNotFoundError,
    ValidationError,
)
from selectiq.domain.models import Project, Proposal, ProposalItem
from selectiq.infrastructure.image_store import ImageStore
from selectiq.infrastructure.project_repository import ProjectRepository, ProposalRepository
from selectiq.intelligence.curator import evidence_weighted, propose

EXPORT_HEADER = ("photo_id", "original_filename")


@dataclass(frozen=True, slots=True)
class SelectionExport:
    filename: str
    content: str
    path: Path
    row_count: int


def format_selection_csv(items: Iterable[ProposalItem]) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(EXPORT_HEADER)
    for item in sorted(items, key=lambda entry: entry.rank):
        if not item.removed:
            writer.writerow((item.photo_id, item.original_filename))
    return output.getvalue()


class RecommendationService:
    def __init__(
        self,
        projects: ProjectRepository,
        proposals: ProposalRepository,
        signal_provider: ProjectSignalProvider,
        export_store: ImageStore,
    ) -> None:
        self.projects = projects
        self.proposals = proposals
        self.signal_provider = signal_provider
        self.export_store = export_store

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

    def remove(self, project_id: str, photo_id: str) -> Proposal:
        return self._set_removed(project_id, photo_id, removed=True)

    def restore(self, project_id: str, photo_id: str) -> Proposal:
        return self._set_removed(project_id, photo_id, removed=False)

    def export(self, project_id: str) -> SelectionExport:
        proposal = self.current(project_id)
        content = format_selection_csv(proposal.items)
        filename = f"selectiq-{project_id[:8]}-v{proposal.version}.csv"
        path = self.export_store.write_export(project_id, filename, content)
        return SelectionExport(filename, content, path, row_count=len(proposal.selected))

    def _set_removed(self, project_id: str, photo_id: str, removed: bool) -> Proposal:
        proposal = self.current(project_id)
        updated = self.proposals.set_removed(proposal.id, photo_id, removed)
        if updated is None:
            raise PhotoNotInProposalError(
                f"Photo {photo_id} is not part of proposal version {proposal.version}."
            )
        return updated

    def _require_project(self, project_id: str) -> Project:
        project = self.projects.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        return project
