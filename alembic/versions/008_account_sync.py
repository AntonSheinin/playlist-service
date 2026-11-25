"""Track account sync and retain the previous token for interrupted rotation."""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_synced", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("users", sa.Column("portal_synced", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("users", sa.Column("auth_previous_token", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "auth_previous_token")
    op.drop_column("users", "portal_synced")
    op.drop_column("users", "auth_synced")
