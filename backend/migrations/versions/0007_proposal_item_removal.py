"""Track photographer removals of proposed photos."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0007_proposal_item_removal"
down_revision: str | None = "0006_recommendation_proposals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("proposal_items") as batch:
        batch.add_column(sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("proposal_items") as batch:
        batch.drop_column("removed_at")
