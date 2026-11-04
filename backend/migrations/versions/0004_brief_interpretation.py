"""Store auditable generative brief interpretations and per-photo guided scores."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_brief_interpretation"
down_revision: str | None = "0003_ai_feature_extraction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brief_interpretations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("provider_called", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("positive_descriptors", sa.JSON()),
        sa.Column("negative_descriptors", sa.JSON()),
        sa.Column("photo_notes", sa.JSON()),
        sa.Column("raw_response", sa.Text()),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("error_message", sa.String(length=1024)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')", name="ck_brief_interpretations_status"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_brief_interpretations_project_id", "brief_interpretations", ["project_id"]
    )
    op.create_table(
        "guided_scores",
        sa.Column("interpretation_id", sa.Uuid(), nullable=False),
        sa.Column("photo_id", sa.Uuid(), nullable=False),
        sa.Column("guided_score", sa.Float(), nullable=False),
        sa.Column("descriptor_score", sa.Float(), nullable=False),
        sa.Column("note_adjustment", sa.Float(), nullable=False),
        sa.Column("brief_relevance", sa.Float()),
        sa.Column("explanation", sa.String(length=2048), nullable=False),
        sa.ForeignKeyConstraint(
            ["interpretation_id"], ["brief_interpretations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("interpretation_id", "photo_id"),
    )


def downgrade() -> None:
    op.drop_table("guided_scores")
    op.drop_index("ix_brief_interpretations_project_id", table_name="brief_interpretations")
    op.drop_table("brief_interpretations")
