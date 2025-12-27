"""Add channel-group association table.

Revision ID: 004
Revises: 003
Create Date: 2025-01-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "group_channels",
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "channel_id"),
    )

    op.execute(
        "INSERT INTO group_channels (group_id, channel_id) "
        "SELECT group_id, id FROM channels WHERE group_id IS NOT NULL"
    )

    with op.batch_alter_table("channels") as batch_op:
        batch_op.drop_column("group_id")


def downgrade() -> None:
    with op.batch_alter_table("channels") as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_channels_group_id_groups",
            "groups",
            ["group_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.execute(
        "UPDATE channels "
        "SET group_id = ("
        "SELECT MIN(group_id) FROM group_channels "
        "WHERE group_channels.channel_id = channels.id"
        ")"
    )

    op.drop_table("group_channels")
