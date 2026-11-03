from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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
from selectiq.domain.models import CreativeBrief, ImportFailure, Photograph, Project


class ProjectRepository(Protocol):
    def save(self, project: Project) -> None: ...

    def get(self, project_id: str) -> Project | None: ...

    def add_photo_if_capacity(self, photo: Photograph, capacity: int) -> bool: ...

    def save_prompt_and_target(self, project_id: str, prompt: str, target: int) -> bool: ...

    def record_import_failure(self, project_id: str, failure: ImportFailure) -> None: ...

    def accepted_count(self, project_id: str) -> int: ...

    def import_failures(self, project_id: str) -> list[ImportFailure]: ...


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
    project: Mapped[ProjectRow] = relationship(back_populates="photos")


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
        )

    @staticmethod
    def _uuid(value: str) -> UUID | None:
        try:
            return UUID(value)
        except (TypeError, ValueError):
            return None
