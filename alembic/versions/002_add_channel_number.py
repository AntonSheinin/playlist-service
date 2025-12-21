"""Add channel_number column to channels table

Revision ID: 002
Revises: 001
Create Date: 2024-12-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("channels", sa.Column("channel_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("channels", "channel_number")
