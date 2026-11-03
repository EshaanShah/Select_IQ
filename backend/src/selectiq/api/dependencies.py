from functools import lru_cache

from selectiq.application.analysis_service import AnalysisService
from selectiq.application.project_service import ProjectService
from selectiq.infrastructure.embedding_cache import NumpyEmbeddingCache
from selectiq.infrastructure.image_store import LocalImageStore
from selectiq.infrastructure.model_adapters import DeterministicVisualEncoder, OpenClipVisualEncoder
from selectiq.infrastructure.project_repository import SqlProjectRepository, create_session_factory
from selectiq.infrastructure.settings import Settings
from selectiq.intelligence.feature_extractor import FeatureExtractor
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
def get_project_service() -> ProjectService:
    settings = get_settings()
    image_store = LocalImageStore(
        data_root=settings.data_root,
        max_file_size_bytes=settings.max_file_size_bytes,
        max_decoded_pixels=settings.max_decoded_pixels,
    )
    return ProjectService(get_repository(), image_store, settings.max_gallery_size)


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
    extractor = FeatureExtractor(
        get_repository(),
        NumpyEmbeddingCache(settings.data_root / "cache"),
        encoder,
        settings.embedding_batch_size,
    )
    return GalleryAnalysisRunner(get_repository(), extractor)


@lru_cache
def get_analysis_service() -> AnalysisService:
    return AnalysisService(get_repository(), get_analysis_runner())
