"""Collect A-07 ranking signals from the A-03, A-04, and A-06 pipelines.

Only photographs whose CLIP analysis completed for the current brief are eligible. AI
guidance is used only when the latest interpretation completed for this brief; otherwise
the signal is absent and the provenance says so rather than substituting anything.
"""

from collections.abc import Callable
from dataclasses import dataclass

from selectiq.application.preference_service import PreferenceService
from selectiq.domain.errors import ValidationError
from selectiq.domain.models import PhotoSignals, Project, SignalProvenance
from selectiq.infrastructure.project_repository import ProjectRepository
from selectiq.intelligence.brief_interpreter import BriefInterpreter, prompt_hash
from selectiq.intelligence.feature_extractor import FeatureExtractor


@dataclass(frozen=True, slots=True)
class SignalBundle:
    signals: list[PhotoSignals]
    provenance: SignalProvenance
    preference_model_version: str


class ProjectSignalProvider:
    def __init__(
        self,
        repository: ProjectRepository,
        extractor: FeatureExtractor,
        interpreter: BriefInterpreter,
        preferences: PreferenceService,
        genuine_encoder: bool,
        genuine_reasoner: bool,
        analysis_running: Callable[[str], bool] = lambda project_id: False,
    ) -> None:
        self.repository = repository
        self.extractor = extractor
        self.interpreter = interpreter
        self.preferences = preferences
        self.genuine_encoder = genuine_encoder
        self.genuine_reasoner = genuine_reasoner
        self.analysis_running = analysis_running

    def collect(self, project: Project) -> SignalBundle:
        if project.brief is None:
            raise ValidationError("Save a creative brief and target before generating a proposal.")
        if self.analysis_running(project.id):
            raise ValidationError(
                "AI analysis or interpretation is still running. Try again when it finishes."
            )
        brief = project.brief.original_text
        analyzed = [
            photo
            for photo in self.interpreter.analyzed_photos(project.id)
            if self.extractor.is_prompt_current(photo, brief)
        ]
        if not analyzed:
            raise ValidationError("Analyze the gallery before generating a proposal.")

        relevance = {
            photo.id: feature.brief_relevance
            for photo in analyzed
            if (feature := self.repository.get_feature(photo.id)) is not None
        }
        guidance = self._guidance(project.id)
        preference = self.preferences.scores(project.id)
        signals = [
            PhotoSignals(
                photo_id=photo.id,
                prompt_relevance=relevance.get(photo.id),
                ai_guidance=guidance.get(photo.id),
                preference=preference.scores.get(photo.id),
            )
            for photo in analyzed
        ]
        return SignalBundle(
            signals=signals,
            provenance=SignalProvenance(
                embedding_model=self._embedding_model(analyzed[0].id),
                embeddings_genuine=self.genuine_encoder,
                guidance_model=f"{self.interpreter.reasoner.provider} / "
                f"{self.interpreter.reasoner.model_name}",
                guidance_status=self._guidance_status(project),
                guidance_genuine=self.genuine_reasoner and bool(guidance),
                comparisons_used=preference.comparisons_used,
                preference_method=preference.method,
                excluded_photo_count=len(project.photos) - len(analyzed),
            ),
            preference_model_version=preference.model_version,
        )

    def _guidance(self, project_id: str) -> dict[str, float]:
        if not self.interpreter.is_current(project_id):
            return {}
        return {
            entry.photo_id: entry.guided_score
            for entry in self.interpreter.ranking(project_id).entries
            if entry.guided_score is not None
        }

    def _guidance_status(self, project: Project) -> str:
        latest = self.repository.latest_interpretation(project.id)
        assert project.brief is not None
        if latest is None or latest.prompt_hash != prompt_hash(project.brief.original_text):
            return "not_started"
        return latest.status

    def _embedding_model(self, photo_id: str) -> str:
        feature = self.repository.get_feature(photo_id)
        assert feature is not None
        return f"{feature.model_name} / {feature.checkpoint}"
