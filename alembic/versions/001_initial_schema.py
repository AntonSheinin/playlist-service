"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create admins table
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admins_username"), "admins", ["username"], unique=True)

    # Create groups table
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_groups_sort_order"), "groups", ["sort_order"], unique=False)

    # Create channels table
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stream_name", sa.String(length=255), nullable=False),
        sa.Column("tvg_name", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("stream_base_url", sa.String(length=500), nullable=False),
        sa.Column("catchup_days", sa.Integer(), nullable=True),
        sa.Column("tvg_id", sa.String(length=100), nullable=True),
        sa.Column("tvg_logo", sa.Text(), nullable=True),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sync_status", sa.String(length=20), nullable=False, server_default="synced"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_channels_stream_name"), "channels", ["stream_name"], unique=True)
    op.create_index(op.f("ix_channels_tvg_id"), "channels", ["tvg_id"], unique=False)
    op.create_index(op.f("ix_channels_sort_order"), "channels", ["sort_order"], unique=False)
    op.create_index(op.f("ix_channels_sync_status"), "channels", ["sync_status"], unique=False)

    # Create packages table
    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create tariffs table
    op.create_table(
        "tariffs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("agreement_number", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="enabled"),
        sa.Column("max_sessions", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("auth_token_id", sa.Integer(), nullable=True),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_users_agreement_number"), "users", ["agreement_number"], unique=True
    )
    op.create_index(op.f("ix_users_token"), "users", ["token"], unique=True)
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)

    # Create package_channels (M:N) table
    op.create_table(
        "package_channels",
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("package_id", "channel_id"),
    )

    # Create tariff_packages (M:N) table
    op.create_table(
        "tariff_packages",
        sa.Column("tariff_id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tariff_id", "package_id"),
    )

    # Create user_tariffs (M:N) table
    op.create_table(
        "user_tariffs",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tariff_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tariff_id"], ["tariffs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "tariff_id"),
    )

    # Create user_packages (M:N) table
    op.create_table(
        "user_packages",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "package_id"),
    )

    # Create user_channels (M:N) table
    op.create_table(
        "user_channels",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "channel_id"),
    )


def downgrade() -> None:
    op.drop_table("user_channels")
    op.drop_table("user_packages")
    op.drop_table("user_tariffs")
    op.drop_table("tariff_packages")
    op.drop_table("package_channels")
    op.drop_index(op.f("ix_users_status"), table_name="users")
    op.drop_index(op.f("ix_users_token"), table_name="users")
    op.drop_index(op.f("ix_users_agreement_number"), table_name="users")
    op.drop_table("users")
    op.drop_table("tariffs")
    op.drop_table("packages")
    op.drop_index(op.f("ix_channels_sync_status"), table_name="channels")
    op.drop_index(op.f("ix_channels_sort_order"), table_name="channels")
    op.drop_index(op.f("ix_channels_tvg_id"), table_name="channels")
    op.drop_index(op.f("ix_channels_stream_name"), table_name="channels")
    op.drop_table("channels")
    op.drop_index(op.f("ix_groups_sort_order"), table_name="groups")
    op.drop_table("groups")
    op.drop_index(op.f("ix_admins_username"), table_name="admins")
    op.drop_table("admins")
