from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import create_engine

from selectiq.application.project_service import ProjectService
from selectiq.infrastructure.image_store import LocalImageStore
from selectiq.infrastructure.project_repository import (
    Base,
    SqlProjectRepository,
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
def project_service(tmp_path) -> ProjectService:
    database_url = f"sqlite:///{tmp_path / 'selectiq-test.sqlite3'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    repository = SqlProjectRepository(create_session_factory(database_url))
    store = LocalImageStore(tmp_path, 25 * 1024 * 1024, 60_000_000)
    return ProjectService(repository, store, max_gallery_size=30)
