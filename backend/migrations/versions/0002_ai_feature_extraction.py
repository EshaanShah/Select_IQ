"""Add versioned photo features and analysis failures."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_ai_feature_extraction"
down_revision: str | None = "0001_project_ingestion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("photos", sa.Column("analysis_error_code", sa.String(length=64)))
    op.add_column("photos", sa.Column("analysis_error_message", sa.String(length=1024)))
    op.create_table(
        "photo_features",
        sa.Column("photo_id", sa.Uuid(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("checkpoint", sa.String(length=256), nullable=False),
        sa.Column("model_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("embedding_path", sa.String(length=4096), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64)),
        sa.Column("brief_relevance", sa.Float()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("embedding_dimension > 0", name="ck_feature_dimension_positive"),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("photo_id"),
    )


def downgrade() -> None:
    op.drop_table("photo_features")
    op.drop_column("photos", "analysis_error_message")
    op.drop_column("photos", "analysis_error_code")
