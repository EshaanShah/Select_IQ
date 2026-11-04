"""Create versioned recommendation proposals with signal provenance."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0006_recommendation_proposals"
down_revision: str | None = "0005_pairwise_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("target_count", sa.Integer(), nullable=False),
        sa.Column("is_genuine_ai", sa.Boolean(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_count > 0", name="ck_proposals_target_positive"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "version", name="uq_proposals_project_version"),
    )
    op.create_index("ix_proposals_project_id", "proposals", ["project_id"], unique=False)
    op.create_table(
        "proposal_items",
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("photo_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("contributions", sa.JSON(), nullable=False),
        sa.CheckConstraint("rank > 0", name="ck_proposal_items_rank_positive"),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("proposal_id", "photo_id"),
        sa.UniqueConstraint("proposal_id", "rank", name="uq_proposal_items_rank"),
    )


def downgrade() -> None:
    op.drop_table("proposal_items")
    op.drop_index("ix_proposals_project_id", table_name="proposals")
    op.drop_table("proposals")
