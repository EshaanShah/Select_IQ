from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import create_engine

from selectiq.application.comparison_service import ComparisonService
from selectiq.application.preference_service import PreferenceService
from selectiq.application.project_service import PhotoUpload, ProjectService
from selectiq.application.proposal_signals import ProjectSignalProvider
from selectiq.application.recommendation_service import RecommendationService
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.image_store import LocalImageStore
from selectiq.infrastructure.model_adapters import DeterministicVisualEncoder
from selectiq.infrastructure.project_repository import (
    Base,
    SqlProjectRepository,
    SqlProposalRepository,
    create_session_factory,
)
from selectiq.infrastructure.reasoners import BriefReasoner, ScriptedBriefReasoner
from selectiq.intelligence.brief_interpreter import BriefInterpreter
from selectiq.intelligence.feature_extractor import FeatureExtractor
from selectiq.intelligence.pair_selector import DeterministicPairSelector
from selectiq.intelligence.preference_model import PairwisePreferenceModel

DEMO_BRIEF = "Peak action and candid celebration; skip empty frames."


def make_jpeg(size: tuple[int, int] = (16, 12), color: str = "#416b55") -> bytes:
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format="JPEG")
    return output.getvalue()


def distinct_jpegs(count: int) -> list[bytes]:
    return [
        make_jpeg(color=f"#{(index * 12) % 256:02x}{(index * 37) % 256:02x}60")
        for index in range(count)
    ]


@pytest.fixture
def jpeg_bytes() -> bytes:
    return make_jpeg()


@pytest.fixture
def project_service(tmp_path) -> ProjectService:
    database_url = f"sqlite:///{tmp_path / 'selectiq-test.sqlite3'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    repository = SqlProjectRepository(create_session_factory(database_url))
    store = LocalImageStore(tmp_path, 25 * 1024 * 1024, 60_000_000)
    return ProjectService(repository, store, max_gallery_size=30)


@dataclass
class AiStack:
    """The A-03 to A-07 services wired over one test database, run synchronously."""

    projects: ProjectService
    extractor: FeatureExtractor
    interpreter: BriefInterpreter
    comparisons: ComparisonService
    preferences: PreferenceService
    proposals: SqlProposalRepository

    def signal_provider(
        self,
        genuine_encoder: bool = False,
        genuine_reasoner: bool = False,
        analysis_running=lambda project_id: False,
    ) -> ProjectSignalProvider:
        return ProjectSignalProvider(
            self.projects.repository,
            self.extractor,
            self.interpreter,
            self.preferences,
            genuine_encoder=genuine_encoder,
            genuine_reasoner=genuine_reasoner,
            analysis_running=analysis_running,
        )

    def recommendations(self, **provider_flags: bool) -> RecommendationService:
        return RecommendationService(
            self.projects.repository,
            self.proposals,
            self.signal_provider(**provider_flags),
            self.projects.image_store,
        )

    def with_reasoner(self, reasoner: BriefReasoner) -> "AiStack":
        interpreter = BriefInterpreter(
            self.projects.repository, self.extractor.cache, self.extractor.encoder, reasoner
        )
        return AiStack(
            self.projects, self.extractor, interpreter, self.comparisons, self.preferences,
            self.proposals,
        )

    def analyzed_gallery(
        self,
        count: int = 18,
        prefix: str = "photo",
        target: int | None = 5,
        brief: str = DEMO_BRIEF,
        uploads: Sequence[PhotoUpload] | None = None,
    ) -> str:
        """Upload, save the brief, then analyze and interpret exactly like GalleryAnalysisRunner."""
        project = self.projects.create_project()
        files = uploads or [
            PhotoUpload(f"{prefix}-{index:02d}.jpg", BytesIO(content))
            for index, content in enumerate(distinct_jpegs(count))
        ]
        accepted = self.projects.import_photos(project.id, list(files)).accepted_count
        if target is not None:
            self.projects.set_prompt_and_target(project.id, brief, min(target, accepted))
        result = self.extractor.analyze(self.projects.repository.list_photos(project.id))
        if result.completed:
            self.extractor.score_prompt(project.id, brief)
            self.interpreter.run(project.id)
        return project.id

    def make_choices(self, project_id: str, count: int, prefer=None) -> None:
        for _ in range(count):
            pair = self.comparisons.next_pair(project_id)
            assert pair is not None
            winner = prefer(pair) if prefer else pair.photo_a_id
            self.comparisons.record_choice(project_id, pair.photo_a_id, pair.photo_b_id, winner)


def build_stack(
    project_service: ProjectService, tmp_path, encoder=None, reasoner: BriefReasoner | None = None
) -> AiStack:
    repository = project_service.repository
    cache = NumpyEmbeddingCache(tmp_path / "embedding-cache")
    encoder = encoder or DeterministicVisualEncoder()
    extractor = FeatureExtractor(repository, cache, encoder)
    return AiStack(
        projects=project_service,
        extractor=extractor,
        interpreter=BriefInterpreter(repository, cache, encoder, reasoner or ScriptedBriefReasoner()),
        comparisons=ComparisonService(repository, DeterministicPairSelector(), comparison_budget=5),
        preferences=PreferenceService(repository, cache, PairwisePreferenceModel(seed=0)),
        proposals=SqlProposalRepository(repository.session_factory),
    )


@pytest.fixture
def stack(project_service: ProjectService, tmp_path) -> AiStack:
    return build_stack(project_service, tmp_path)
