import os
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import create_engine, text

from selectiq.application.project_service import ProjectService
from selectiq.infrastructure.image_store import LocalImageStore
from selectiq.infrastructure.project_repository import (
    PostgresProjectRepository,
    create_session_factory,
)


def make_jpeg(size: tuple[int, int] = (16, 12), color: str = "#416b55") -> bytes:
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format="JPEG")
    return output.getvalue()


@pytest.fixture
def jpeg_bytes() -> bytes:
    return make_jpeg()


@pytest.fixture
def database_url() -> str:
    value = os.getenv("SELECTIQ_TEST_DATABASE_URL")
    if not value:
        pytest.skip("SELECTIQ_TEST_DATABASE_URL is required for PostgreSQL integration tests")
    return value


@pytest.fixture
def project_service(database_url: str, tmp_path) -> ProjectService:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE photo_import_failures, photos, projects CASCADE"))
    repository = PostgresProjectRepository(create_session_factory(database_url))
    store = LocalImageStore(tmp_path, 25 * 1024 * 1024, 60_000_000)
    return ProjectService(repository, store, max_gallery_size=300)
