from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_registry_settings"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registry_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("downloads_locked", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("registry_settings")
