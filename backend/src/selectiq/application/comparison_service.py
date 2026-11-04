"""Persistent pairwise-feedback workflow for Alpha story A-05."""

from dataclasses import dataclass

from selectiq.domain.errors import (
    DuplicateComparisonError,
    ProjectNotFoundError,
    ValidationError,
)
from selectiq.domain.models import ComparisonChoice
from selectiq.infrastructure.project_repository import ProjectRepository
from selectiq.intelligence.pair_selector import DeterministicPairSelector


@dataclass(frozen=True, slots=True)
class ComparisonPair:
    photo_a_id: str
    photo_b_id: str
    sequence: int
    budget: int


class ComparisonService:
    def __init__(
        self,
        repository: ProjectRepository,
        pair_selector: DeterministicPairSelector,
        comparison_budget: int,
    ) -> None:
        self.repository = repository
        self.pair_selector = pair_selector
        self.comparison_budget = comparison_budget

    def next_pair(self, project_id: str) -> ComparisonPair | None:
        project = self._require_project(project_id)
        choices = self.repository.comparison_choices(project_id)
        if len(choices) >= self.comparison_budget:
            return None
        # The selector orders by identifier; stable keys keep pairs identical for the same
        # files across fresh projects, since photo UUIDs are random per upload.
        ordered = sorted(
            project.photos, key=lambda photo: (photo.original_filename, photo.content_hash, photo.id)
        )
        key_of = {photo.id: f"{index:04d}" for index, photo in enumerate(ordered)}
        photo_of = {key: photo_id for photo_id, key in key_of.items()}
        previous = {
            frozenset((key_of[choice.winner_id], key_of[choice.loser_id]))
            for choice in choices
            if choice.winner_id in key_of and choice.loser_id in key_of
        }
        pair = self.pair_selector.select(list(photo_of), previous)
        if pair is None:
            return None
        return ComparisonPair(
            photo_of[pair[0]], photo_of[pair[1]], len(choices) + 1, self.comparison_budget
        )

    def record_choice(
        self, project_id: str, photo_a_id: str, photo_b_id: str, winner_id: str
    ) -> ComparisonChoice:
        project = self._require_project(project_id)
        choices = self.repository.comparison_choices(project_id)
        if len(choices) >= self.comparison_budget:
            raise ValidationError("The comparison budget is complete.")
        if photo_a_id == photo_b_id:
            raise ValidationError("A comparison requires two distinct photos.")

        project_photo_ids = {photo.id for photo in project.photos}
        if any(
            photo_id not in project_photo_ids
            for photo_id in (photo_a_id, photo_b_id, winner_id)
        ):
            raise ValidationError("Every comparison photo must belong to the current project.")
        if winner_id not in {photo_a_id, photo_b_id}:
            raise ValidationError("The winner must be one of the presented pair.")
        if self.repository.has_comparison(project_id, photo_a_id, photo_b_id):
            raise DuplicateComparisonError("This pair has already been compared.")

        loser_id = photo_b_id if winner_id == photo_a_id else photo_a_id
        choice = ComparisonChoice(
            project_id=project_id,
            winner_id=winner_id,
            loser_id=loser_id,
            sequence=len(choices) + 1,
        )
        self.repository.save_comparison(choice)
        return choice

    def choices(self, project_id: str) -> list[ComparisonChoice]:
        self._require_project(project_id)
        return self.repository.comparison_choices(project_id)

    def _require_project(self, project_id: str):
        project = self.repository.get(project_id)
        if project is None:
            raise ProjectNotFoundError(f"Project {project_id} was not found.")
        return project

