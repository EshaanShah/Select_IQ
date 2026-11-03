from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from selectiq.domain.enums import ProcessingState
from selectiq.domain.models import CreativeBrief, ImportFailure, PhotoFeature, Photograph, Project


class ProjectRepository(Protocol):
    def save(self, project: Project) -> None: ...

    def get(self, project_id: str) -> Project | None: ...

    def add_photo_if_capacity(self, photo: Photograph, capacity: int) -> bool: ...

    def save_prompt_and_target(self, project_id: str, prompt: str, target: int) -> bool: ...

    def record_import_failure(self, project_id: str, failure: ImportFailure) -> None: ...

    def accepted_count(self, project_id: str) -> int: ...

    def import_failures(self, project_id: str) -> list[ImportFailure]: ...

    def list_photos(self, project_id: str) -> list[Photograph]: ...

    def get_feature(self, photo_id: str) -> PhotoFeature | None: ...

    def mark_photo_processing(self, photo_id: str) -> None: ...

    def mark_photo_failed(self, photo_id: str, code: str, message: str) -> None: ...

    def save_feature(self, feature: PhotoFeature) -> None: ...

    def update_relevance(self, photo_id: str, prompt_hash: str, score: float) -> None: ...


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "target_count IS NULL OR target_count >= 1",
            name="ck_projects_target_count_positive",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    brief_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photos: Mapped[list["PhotoRow"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class PhotoRow(Base):
    __tablename__ = "photos"
    __table_args__ = (
        CheckConstraint("width > 0", name="ck_photos_width_positive"),
        CheckConstraint("height > 0", name="ck_photos_height_positive"),
        CheckConstraint("byte_size >= 0", name="ck_photos_byte_size_nonnegative"),
        CheckConstraint(
            "processing_state IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_photos_processing_state",
        ),
        Index("ix_photos_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(4096), unique=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_state: Mapped[str] = mapped_column(String(16), nullable=False)
    analysis_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    analysis_error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    project: Mapped[ProjectRow] = relationship(back_populates="photos")


class PhotoFeatureRow(Base):
    __tablename__ = "photo_features"
    __table_args__ = (
        CheckConstraint("embedding_dimension > 0", name="ck_feature_dimension_positive"),
    )

    photo_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    checkpoint: Mapped[str] = mapped_column(String(256), nullable=False)
    model_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_path: Mapped[str] = mapped_column(String(4096), nullable=False)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    brief_relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ImportFailureRow(Base):
    __tablename__ = "photo_import_failures"
    __table_args__ = (Index("ix_photo_import_failures_project_id", "project_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(1024), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    return sessionmaker(engine, expire_on_commit=False)


class SqlProjectRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory
        self._write_lock = Lock()

    def save(self, project: Project) -> None:
        with self.session_factory.begin() as session:
            session.add(ProjectRow(id=UUID(project.id)))

    def get(self, project_id: str) -> Project | None:
        project_uuid = self._uuid(project_id)
        if project_uuid is None:
            return None
        with self.session_factory() as session:
            row = session.get(ProjectRow, project_uuid)
            if row is None:
                return None
            photo_rows = session.scalars(
                select(PhotoRow).where(PhotoRow.project_id == project_uuid).order_by(PhotoRow.id)
            ).all()
            brief = (
                CreativeBrief(project_id=str(row.id), original_text=row.brief_text)
                if row.brief_text is not None
                else None
            )
            return Project(
                id=str(row.id),
                target_count=row.target_count,
                brief=brief,
                photos=[self._to_photo(photo) for photo in photo_rows],
            )

    def save_prompt_and_target(self, project_id: str, prompt: str, target: int) -> bool:
        project_uuid = self._uuid(project_id)
        if project_uuid is None:
            return False
        with self._write_lock, self.session_factory.begin() as session:
            project = session.get(ProjectRow, project_uuid)
            if project is None:
                return False
            project.brief_text = prompt
            project.target_count = target
            return True

    def add_photo_if_capacity(self, photo: Photograph, capacity: int) -> bool:
        project_uuid = UUID(photo.project_id)
        with self._write_lock, self.session_factory.begin() as session:
            project = session.get(ProjectRow, project_uuid)
            if project is None:
                return False
            count = session.scalar(
                select(func.count())
                .select_from(PhotoRow)
                .where(PhotoRow.project_id == project_uuid)
            )
            if int(count or 0) >= capacity:
                return False
            session.add(
                PhotoRow(
                    id=UUID(photo.id),
                    project_id=project_uuid,
                    original_filename=photo.original_filename,
                    storage_path=str(photo.working_path),
                    content_hash=photo.content_hash,
                    width=photo.width,
                    height=photo.height,
                    byte_size=photo.byte_size,
                    processing_state=photo.state.value,
                )
            )
            return True

    def record_import_failure(self, project_id: str, failure: ImportFailure) -> None:
        with self.session_factory.begin() as session:
            session.add(
                ImportFailureRow(
                    id=uuid4(),
                    project_id=UUID(project_id),
                    filename=failure.filename,
                    code=failure.code,
                    message=failure.message,
                )
            )

    def accepted_count(self, project_id: str) -> int:
        project_uuid = UUID(project_id)
        with self.session_factory() as session:
            count = session.scalar(
                select(func.count()).select_from(PhotoRow).where(PhotoRow.project_id == project_uuid)
            )
            return int(count or 0)

    def import_failures(self, project_id: str) -> list[ImportFailure]:
        project_uuid = UUID(project_id)
        with self.session_factory() as session:
            rows = session.scalars(
                select(ImportFailureRow)
                .where(ImportFailureRow.project_id == project_uuid)
                .order_by(ImportFailureRow.created_at, ImportFailureRow.id)
            ).all()
            return [
                ImportFailure(
                    filename=row.filename,
                    code=row.code,
                    message=row.message,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    def list_photos(self, project_id: str) -> list[Photograph]:
        project_uuid = self._uuid(project_id)
        if project_uuid is None:
            return []
        with self.session_factory() as session:
            rows = session.scalars(
                select(PhotoRow).where(PhotoRow.project_id == project_uuid).order_by(PhotoRow.id)
            ).all()
            return [self._to_photo(row) for row in rows]

    def get_feature(self, photo_id: str) -> PhotoFeature | None:
        photo_uuid = self._uuid(photo_id)
        if photo_uuid is None:
            return None
        with self.session_factory() as session:
            row = session.get(PhotoFeatureRow, photo_uuid)
            return self._to_feature(row) if row is not None else None

    def mark_photo_processing(self, photo_id: str) -> None:
        with self.session_factory.begin() as session:
            row = session.get(PhotoRow, UUID(photo_id))
            if row is not None:
                row.processing_state = ProcessingState.PROCESSING.value
                row.analysis_error_code = None
                row.analysis_error_message = None

    def mark_photo_failed(self, photo_id: str, code: str, message: str) -> None:
        with self.session_factory.begin() as session:
            row = session.get(PhotoRow, UUID(photo_id))
            if row is not None:
                row.processing_state = ProcessingState.FAILED.value
                row.analysis_error_code = code
                row.analysis_error_message = message[:1024]

    def save_feature(self, feature: PhotoFeature) -> None:
        with self.session_factory.begin() as session:
            photo_uuid = UUID(feature.photo_id)
            row = session.get(PhotoFeatureRow, photo_uuid)
            values = {
                "model_name": feature.model_name,
                "checkpoint": feature.checkpoint,
                "model_fingerprint": feature.model_fingerprint,
                "embedding_dimension": feature.embedding_dimension,
                "embedding_path": str(feature.embedding_path),
                "prompt_hash": feature.prompt_hash,
                "brief_relevance": feature.brief_relevance,
            }
            if row is None:
                session.add(PhotoFeatureRow(photo_id=photo_uuid, **values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
            photo = session.get(PhotoRow, photo_uuid)
            if photo is not None:
                photo.processing_state = ProcessingState.COMPLETED.value
                photo.analysis_error_code = None
                photo.analysis_error_message = None

    def update_relevance(self, photo_id: str, prompt_hash: str, score: float) -> None:
        with self.session_factory.begin() as session:
            row = session.get(PhotoFeatureRow, UUID(photo_id))
            if row is None:
                raise ValueError(f"Photo {photo_id} has no embedding.")
            row.prompt_hash = prompt_hash
            row.brief_relevance = score

    @staticmethod
    def _to_photo(row: PhotoRow) -> Photograph:
        return Photograph(
            id=str(row.id),
            project_id=str(row.project_id),
            original_filename=row.original_filename,
            working_path=Path(row.storage_path),
            content_hash=row.content_hash,
            width=row.width,
            height=row.height,
            byte_size=row.byte_size,
            state=ProcessingState(row.processing_state),
            analysis_error_code=row.analysis_error_code,
            analysis_error_message=row.analysis_error_message,
        )

    @staticmethod
    def _to_feature(row: PhotoFeatureRow) -> PhotoFeature:
        return PhotoFeature(
            photo_id=str(row.photo_id),
            model_name=row.model_name,
            checkpoint=row.checkpoint,
            model_fingerprint=row.model_fingerprint,
            embedding_dimension=row.embedding_dimension,
            embedding_path=Path(row.embedding_path),
            prompt_hash=row.prompt_hash,
            brief_relevance=row.brief_relevance,
        )

    @staticmethod
    def _uuid(value: str) -> UUID | None:
        try:
            return UUID(value)
        except (TypeError, ValueError):
            return None
