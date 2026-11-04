from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
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
from selectiq.domain.models import (
    BriefInterpretation,
    ComparisonChoice,
    CreativeBrief,
    GuidedScore,
    ImportFailure,
    PhotoFeature,
    Photograph,
    PhotoNote,
    Project,
    Proposal,
    ProposalItem,
    SignalProvenance,
)


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

    def save_interpretation(
        self, interpretation: BriefInterpretation, scores: list[GuidedScore]
    ) -> None: ...

    def latest_interpretation(self, project_id: str) -> BriefInterpretation | None: ...

    def guided_scores(self, interpretation_id: str) -> list[GuidedScore]: ...

    def provider_call_count(self, project_id: str) -> int: ...

    def comparison_choices(self, project_id: str) -> list[ComparisonChoice]: ...

    def has_comparison(self, project_id: str, photo_a_id: str, photo_b_id: str) -> bool: ...

    def save_comparison(self, choice: ComparisonChoice) -> None: ...


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


class BriefInterpretationRow(Base):
    __tablename__ = "brief_interpretations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'failed')", name="ck_brief_interpretations_status"
        ),
        Index("ix_brief_interpretations_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_called: Mapped[bool] = mapped_column(Boolean, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    positive_descriptors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    negative_descriptors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    photo_notes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GuidedScoreRow(Base):
    __tablename__ = "guided_scores"

    interpretation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("brief_interpretations.id", ondelete="CASCADE"), primary_key=True
    )
    photo_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True
    )
    guided_score: Mapped[float] = mapped_column(Float, nullable=False)
    descriptor_score: Mapped[float] = mapped_column(Float, nullable=False)
    note_adjustment: Mapped[float] = mapped_column(Float, nullable=False)
    brief_relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    explanation: Mapped[str] = mapped_column(String(2048), nullable=False)


class ComparisonChoiceRow(Base):
    __tablename__ = "comparison_choices"
    __table_args__ = (
        CheckConstraint("winner_id != loser_id", name="ck_comparison_distinct_photos"),
        UniqueConstraint("project_id", "sequence", name="uq_comparison_project_sequence"),
        UniqueConstraint(
            "project_id", "photo_low_id", "photo_high_id", name="uq_comparison_project_pair"
        ),
        Index("ix_comparison_choices_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    winner_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False
    )
    loser_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False
    )
    photo_low_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    photo_high_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProposalRow(Base):
    __tablename__ = "proposals"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_proposals_project_version"),
        CheckConstraint("target_count > 0", name="ck_proposals_target_positive"),
        Index("ix_proposals_project_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_genuine_ai: Mapped[bool] = mapped_column(Boolean, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProposalItemRow(Base):
    __tablename__ = "proposal_items"
    __table_args__ = (
        UniqueConstraint("proposal_id", "rank", name="uq_proposal_items_rank"),
        CheckConstraint("rank > 0", name="ck_proposal_items_rank_positive"),
    )

    proposal_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("proposals.id", ondelete="CASCADE"), primary_key=True
    )
    photo_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    contributions: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)


class ProposalRepository(Protocol):
    def create(
        self,
        project_id: str,
        target_count: int,
        provenance: SignalProvenance,
        parameters: dict[str, object],
        items: Sequence[ProposalItem],
    ) -> Proposal: ...

    def latest(self, project_id: str) -> Proposal | None: ...


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

    def save_interpretation(
        self, interpretation: BriefInterpretation, scores: list[GuidedScore]
    ) -> None:
        project_uuid = UUID(interpretation.project_id)
        with self._write_lock, self.session_factory.begin() as session:
            sequence = session.scalar(
                select(func.coalesce(func.max(BriefInterpretationRow.sequence), 0)).where(
                    BriefInterpretationRow.project_id == project_uuid
                )
            )
            interpretation_uuid = UUID(interpretation.id)
            session.add(
                BriefInterpretationRow(
                    id=interpretation_uuid,
                    project_id=project_uuid,
                    prompt_hash=interpretation.prompt_hash,
                    status=interpretation.status,
                    provider=interpretation.provider,
                    model_name=interpretation.model_name,
                    provider_called=interpretation.provider_called,
                    summary=interpretation.summary,
                    positive_descriptors=list(interpretation.positive_descriptors),
                    negative_descriptors=list(interpretation.negative_descriptors),
                    photo_notes=[
                        {"photo_id": note.photo_id, "effect": note.effect, "reason": note.reason}
                        for note in interpretation.photo_notes
                    ],
                    raw_response=interpretation.raw_response,
                    error_code=interpretation.error_code,
                    error_message=(interpretation.error_message or None)
                    and interpretation.error_message[:1024],
                    duration_ms=interpretation.duration_ms,
                    input_tokens=interpretation.input_tokens,
                    output_tokens=interpretation.output_tokens,
                    sequence=int(sequence or 0) + 1,
                )
            )
            session.flush()
            for score in scores:
                session.add(
                    GuidedScoreRow(
                        interpretation_id=interpretation_uuid,
                        photo_id=UUID(score.photo_id),
                        guided_score=score.guided_score,
                        descriptor_score=score.descriptor_score,
                        note_adjustment=score.note_adjustment,
                        brief_relevance=score.brief_relevance,
                        explanation=score.explanation[:2048],
                    )
                )

    def latest_interpretation(self, project_id: str) -> BriefInterpretation | None:
        project_uuid = self._uuid(project_id)
        if project_uuid is None:
            return None
        with self.session_factory() as session:
            row = session.scalars(
                select(BriefInterpretationRow)
                .where(BriefInterpretationRow.project_id == project_uuid)
                .order_by(BriefInterpretationRow.sequence.desc())
                .limit(1)
            ).first()
            return self._to_interpretation(row) if row is not None else None

    def guided_scores(self, interpretation_id: str) -> list[GuidedScore]:
        interpretation_uuid = self._uuid(interpretation_id)
        if interpretation_uuid is None:
            return []
        with self.session_factory() as session:
            rows = session.scalars(
                select(GuidedScoreRow)
                .where(GuidedScoreRow.interpretation_id == interpretation_uuid)
                .order_by(GuidedScoreRow.guided_score.desc(), GuidedScoreRow.photo_id)
            ).all()
            return [
                GuidedScore(
                    photo_id=str(row.photo_id),
                    guided_score=row.guided_score,
                    descriptor_score=row.descriptor_score,
                    note_adjustment=row.note_adjustment,
                    brief_relevance=row.brief_relevance,
                    explanation=row.explanation,
                )
                for row in rows
            ]

    def provider_call_count(self, project_id: str) -> int:
        project_uuid = self._uuid(project_id)
        if project_uuid is None:
            return 0
        with self.session_factory() as session:
            count = session.scalar(
                select(func.count())
                .select_from(BriefInterpretationRow)
                .where(
                    BriefInterpretationRow.project_id == project_uuid,
                    BriefInterpretationRow.provider_called.is_(True),
                )
            )
            return int(count or 0)

    def comparison_choices(self, project_id: str) -> list[ComparisonChoice]:
        project_uuid = self._uuid(project_id)
        if project_uuid is None:
            return []
        with self.session_factory() as session:
            rows = session.scalars(
                select(ComparisonChoiceRow)
                .where(ComparisonChoiceRow.project_id == project_uuid)
                .order_by(ComparisonChoiceRow.sequence)
            ).all()
            return [
                ComparisonChoice(
                    project_id=str(row.project_id),
                    winner_id=str(row.winner_id),
                    loser_id=str(row.loser_id),
                    sequence=row.sequence,
                    reason=row.reason,
                )
                for row in rows
            ]

    def has_comparison(self, project_id: str, photo_a_id: str, photo_b_id: str) -> bool:
        project_uuid = self._uuid(project_id)
        photo_ids = sorted((UUID(photo_a_id), UUID(photo_b_id)), key=str)
        if project_uuid is None:
            return False
        with self.session_factory() as session:
            count = session.scalar(
                select(func.count())
                .select_from(ComparisonChoiceRow)
                .where(
                    ComparisonChoiceRow.project_id == project_uuid,
                    ComparisonChoiceRow.photo_low_id == photo_ids[0],
                    ComparisonChoiceRow.photo_high_id == photo_ids[1],
                )
            )
            return bool(count)

    def save_comparison(self, choice: ComparisonChoice) -> None:
        ordered = sorted((UUID(choice.winner_id), UUID(choice.loser_id)), key=str)
        with self._write_lock, self.session_factory.begin() as session:
            session.add(
                ComparisonChoiceRow(
                    id=uuid4(),
                    project_id=UUID(choice.project_id),
                    winner_id=UUID(choice.winner_id),
                    loser_id=UUID(choice.loser_id),
                    photo_low_id=ordered[0],
                    photo_high_id=ordered[1],
                    sequence=choice.sequence,
                    reason=choice.reason,
                )
            )

    @staticmethod
    def _to_interpretation(row: BriefInterpretationRow) -> BriefInterpretation:
        return BriefInterpretation(
            id=str(row.id),
            project_id=str(row.project_id),
            prompt_hash=row.prompt_hash,
            status=row.status,
            provider=row.provider,
            model_name=row.model_name,
            provider_called=row.provider_called,
            summary=row.summary,
            positive_descriptors=tuple(row.positive_descriptors or ()),
            negative_descriptors=tuple(row.negative_descriptors or ()),
            photo_notes=tuple(
                PhotoNote(note["photo_id"], note["effect"], note["reason"])
                for note in row.photo_notes or ()
            ),
            raw_response=row.raw_response,
            error_code=row.error_code,
            error_message=row.error_message,
            duration_ms=row.duration_ms,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            created_at=row.created_at,
        )

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


class SqlProposalRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory
        self._write_lock = Lock()

    def create(
        self,
        project_id: str,
        target_count: int,
        provenance: SignalProvenance,
        parameters: dict[str, object],
        items: Sequence[ProposalItem],
    ) -> Proposal:
        project_uuid = UUID(project_id)
        proposal_id = uuid4()
        with self._write_lock, self.session_factory.begin() as session:
            current = session.scalar(
                select(func.max(ProposalRow.version)).where(ProposalRow.project_id == project_uuid)
            )
            session.add(
                ProposalRow(
                    id=proposal_id,
                    project_id=project_uuid,
                    version=int(current or 0) + 1,
                    target_count=target_count,
                    is_genuine_ai=provenance.is_genuine_ai,
                    provenance=asdict(provenance),
                    parameters=parameters,
                )
            )
            session.flush()
            session.add_all(
                ProposalItemRow(
                    proposal_id=proposal_id,
                    photo_id=UUID(item.photo_id),
                    rank=item.rank,
                    score=item.score,
                    contributions=item.contributions,
                )
                for item in items
            )
        proposal = self._load(proposal_id)
        assert proposal is not None
        return proposal

    def latest(self, project_id: str) -> Proposal | None:
        project_uuid = SqlProjectRepository._uuid(project_id)
        if project_uuid is None:
            return None
        with self.session_factory() as session:
            proposal_id = session.scalar(
                select(ProposalRow.id)
                .where(ProposalRow.project_id == project_uuid)
                .order_by(ProposalRow.version.desc())
                .limit(1)
            )
        return None if proposal_id is None else self._load(proposal_id)

    def _load(self, proposal_id: UUID) -> Proposal | None:
        with self.session_factory() as session:
            row = session.get(ProposalRow, proposal_id)
            if row is None:
                return None
            item_rows = session.execute(
                select(ProposalItemRow, PhotoRow.original_filename)
                .join(PhotoRow, PhotoRow.id == ProposalItemRow.photo_id)
                .where(ProposalItemRow.proposal_id == proposal_id)
                .order_by(ProposalItemRow.rank)
            ).all()
            return Proposal(
                id=str(row.id),
                project_id=str(row.project_id),
                version=row.version,
                target_count=row.target_count,
                provenance=SignalProvenance(**row.provenance),
                parameters=dict(row.parameters),
                items=tuple(
                    ProposalItem(
                        photo_id=str(item.photo_id),
                        original_filename=filename,
                        rank=item.rank,
                        score=item.score,
                        contributions=dict(item.contributions),
                    )
                    for item, filename in item_rows
                ),
                created_at=row.created_at,
            )
