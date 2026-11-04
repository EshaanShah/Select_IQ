from functools import lru_cache

from selectiq.application.analysis_service import AnalysisService
from selectiq.application.comparison_service import ComparisonService
from selectiq.application.preference_service import PreferenceService
from selectiq.application.project_service import ProjectService
from selectiq.application.proposal_signals import ProjectSignalProvider
from selectiq.application.recommendation_service import RecommendationService
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.image_store import LocalImageStore
from selectiq.infrastructure.model_adapters import DeterministicVisualEncoder, OpenClipVisualEncoder
from selectiq.infrastructure.project_repository import (
    SqlProjectRepository,
    SqlProposalRepository,
    create_session_factory,
)
from selectiq.infrastructure.reasoners import (
    BriefReasoner,
    GroqBriefReasoner,
    ScriptedBriefReasoner,
)
from selectiq.infrastructure.settings import Settings
from selectiq.intelligence.brief_interpreter import BriefInterpreter
from selectiq.intelligence.feature_extractor import FeatureExtractor
from selectiq.intelligence.pair_selector import DeterministicPairSelector
from selectiq.intelligence.preference_model import PairwisePreferenceModel
from selectiq.jobs.analyze_gallery import GalleryAnalysisRunner


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_directories()
    return settings


@lru_cache
def get_repository() -> SqlProjectRepository:
    settings = get_settings()
    return SqlProjectRepository(create_session_factory(settings.database_url))


@lru_cache
def get_image_store() -> LocalImageStore:
    settings = get_settings()
    return LocalImageStore(
        data_root=settings.data_root,
        max_file_size_bytes=settings.max_file_size_bytes,
        max_decoded_pixels=settings.max_decoded_pixels,
    )


@lru_cache
def get_project_service() -> ProjectService:
    settings = get_settings()
    return ProjectService(get_repository(), get_image_store(), settings.max_gallery_size)


@lru_cache
def get_analysis_runner() -> GalleryAnalysisRunner:
    settings = get_settings()
    if settings.model_adapter == "fake":
        encoder = DeterministicVisualEncoder()
    elif settings.model_adapter == "openclip":
        encoder = OpenClipVisualEncoder(
            settings.embedding_model,
            settings.embedding_checkpoint,
            settings.embedding_device,
            settings.feature_version,
        )
    else:
        raise ValueError(f"Unknown model adapter: {settings.model_adapter}")
    cache = NumpyEmbeddingCache(settings.data_root / "cache")
    extractor = FeatureExtractor(get_repository(), cache, encoder, settings.embedding_batch_size)
    interpreter = BriefInterpreter(
        get_repository(),
        cache,
        encoder,
        build_reasoner(settings),
        settings.reasoner_max_requests_per_project,
    )
    return GalleryAnalysisRunner(get_repository(), extractor, interpreter)


def build_reasoner(settings: Settings) -> BriefReasoner:
    if settings.reasoner == "groq":
        return GroqBriefReasoner(
            settings.groq_api_key, settings.groq_model, settings.reasoner_timeout_seconds
        )
    if settings.reasoner == "fake":
        return ScriptedBriefReasoner()
    raise ValueError(f"Unknown reasoner: {settings.reasoner}")


@lru_cache
def get_analysis_service() -> AnalysisService:
    return AnalysisService(get_repository(), get_analysis_runner())


@lru_cache
def get_comparison_service() -> ComparisonService:
    settings = get_settings()
    return ComparisonService(
        get_repository(), DeterministicPairSelector(), settings.comparison_budget
    )


@lru_cache
def get_preference_service() -> PreferenceService:
    settings = get_settings()
    return PreferenceService(
        get_repository(),
        NumpyEmbeddingCache(settings.data_root / "cache"),
        PairwisePreferenceModel(seed=0),
    )


@lru_cache
def get_recommendation_service() -> RecommendationService:
    settings = get_settings()
    runner = get_analysis_runner()
    assert runner.interpreter is not None
    provider = ProjectSignalProvider(
        get_repository(),
        runner.extractor,
        runner.interpreter,
        get_preference_service(),
        genuine_encoder=settings.model_adapter == "openclip",
        genuine_reasoner=settings.reasoner == "groq",
        analysis_running=runner.is_active,
    )
    return RecommendationService(
        get_repository(),
        SqlProposalRepository(get_repository().session_factory),
        provider,
        get_image_store(),
    )
