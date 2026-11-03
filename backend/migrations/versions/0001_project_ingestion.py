"""Create project ingestion tables."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_project_ingestion"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "photos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=1024), nullable=False),
        sa.Column("storage_path", sa.String(length=4096), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("processing_state", sa.String(length=16), nullable=False),
        sa.CheckConstraint("byte_size >= 0", name="ck_photos_byte_size_nonnegative"),
        sa.CheckConstraint("height > 0", name="ck_photos_height_positive"),
        sa.CheckConstraint(
            "processing_state IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_photos_processing_state",
        ),
        sa.CheckConstraint("width > 0", name="ck_photos_width_positive"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index("ix_photos_project_id", "photos", ["project_id"], unique=False)
    op.create_table(
        "photo_import_failures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=1024), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_photo_import_failures_project_id",
        "photo_import_failures",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_photo_import_failures_project_id", table_name="photo_import_failures")
    op.drop_table("photo_import_failures")
    op.drop_index("ix_photos_project_id", table_name="photos")
    op.drop_table("photos")
    op.drop_table("projects")
