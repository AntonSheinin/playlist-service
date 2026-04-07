"""Add source to channels and make stream names provider-scoped.

Revision ID: 005
Revises: 004
Create Date: 2026-04-05 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "channels",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="flussonic"),
    )
    op.alter_column("channels", "source", server_default=None)
    op.create_index("ix_channels_source", "channels", ["source"], unique=False)

    op.drop_index("ix_channels_stream_name", table_name="channels")
    op.create_index("ix_channels_stream_name", "channels", ["stream_name"], unique=False)
    op.create_unique_constraint(
        "uq_channels_source_stream_name",
        "channels",
        ["source", "stream_name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_channels_source_stream_name", "channels", type_="unique")
    op.drop_index("ix_channels_stream_name", table_name="channels")
    op.create_index("ix_channels_stream_name", "channels", ["stream_name"], unique=True)
    op.drop_index("ix_channels_source", table_name="channels")
    op.drop_column("channels", "source")
