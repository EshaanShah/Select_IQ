from functools import lru_cache

from selectiq.application.project_service import ProjectService
from selectiq.infrastructure.image_store import LocalImageStore
from selectiq.infrastructure.project_repository import SqlProjectRepository, create_session_factory
from selectiq.infrastructure.settings import Settings


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_directories()
    return settings


@lru_cache
def get_project_service() -> ProjectService:
    settings = get_settings()
    repository = SqlProjectRepository(create_session_factory(settings.database_url))
    image_store = LocalImageStore(
        data_root=settings.data_root,
        max_file_size_bytes=settings.max_file_size_bytes,
        max_decoded_pixels=settings.max_decoded_pixels,
    )
    return ProjectService(repository, image_store, settings.max_gallery_size)
