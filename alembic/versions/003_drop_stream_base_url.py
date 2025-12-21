"""Drop stream_base_url from channels

Revision ID: 003
Revises: 002
Create Date: 2024-12-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("channels", "stream_base_url")


def downgrade() -> None:
    op.add_column(
        "channels",
        sa.Column("stream_base_url", sa.String(length=500), nullable=False, server_default=""),
    )
    op.alter_column("channels", "stream_base_url", server_default=None)
