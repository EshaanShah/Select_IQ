"""Persist project-scoped pairwise comparison choices."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_pairwise_feedback"
down_revision: str | None = "0004_brief_interpretation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comparison_choices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("winner_id", sa.Uuid(), nullable=False),
        sa.Column("loser_id", sa.Uuid(), nullable=False),
        sa.Column("photo_low_id", sa.Uuid(), nullable=False),
        sa.Column("photo_high_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=1024)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("winner_id != loser_id", name="ck_comparison_distinct_photos"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_id"], ["photos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["loser_id"], ["photos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "sequence", name="uq_comparison_project_sequence"),
        sa.UniqueConstraint(
            "project_id", "photo_low_id", "photo_high_id", name="uq_comparison_project_pair"
        ),
    )
    op.create_index("ix_comparison_choices_project_id", "comparison_choices", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_comparison_choices_project_id", table_name="comparison_choices")
    op.drop_table("comparison_choices")
