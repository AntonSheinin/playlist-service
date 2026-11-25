"""Store an account's maximum number of Portal devices."""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("max_portal_devices", sa.Integer(), server_default="1", nullable=False)
    )
    op.create_check_constraint(
        "ck_users_max_portal_devices_positive", "users", "max_portal_devices >= 1"
    )
    users = sa.table("users", sa.column("portal_synced", sa.Boolean()))
    op.execute(users.update().where(users.c.portal_synced.is_(True)).values(portal_synced=False))


def downgrade() -> None:
    op.drop_constraint("ck_users_max_portal_devices_positive", "users", type_="check")
    op.drop_column("users", "max_portal_devices")
