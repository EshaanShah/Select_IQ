"""Store the project prompt and target."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_prompt_target"
down_revision: str | None = "0001_project_ingestion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("brief_text", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("target_count", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_projects_target_count_positive",
            "target_count IS NULL OR target_count >= 1",
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("ck_projects_target_count_positive", type_="check")
        batch_op.drop_column("target_count")
        batch_op.drop_column("brief_text")
