"""Persist playlist URL names and enforce case-insensitive uniqueness.

Revision ID: 007
Revises: 006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("first_name", sa.String),
        sa.column("last_name", sa.String),
        sa.column("agreement_number", sa.String),
        sa.column("playlist_name", sa.String(302)),
    )
    rows = connection.execute(
        sa.select(users.c.id, users.c.first_name, users.c.last_name, users.c.agreement_number)
    ).mappings().all()
    values = []
    for user in rows:
        # Frozen copy of the pre-007 filename sanitizer. Do not import application code.
        parts = []
        for field in ("last_name", "first_name", "agreement_number"):
            value = user[field].replace(" ", "_")
            parts.append("".join(char for char in value if char.isalnum() or char in "_-"))
        name = "_".join(parts)
        if not 1 <= len(name) <= 302:
            raise RuntimeError(f"Invalid generated playlist name for user {user['id']}: {name!r}")
        values.append({"user_id": user["id"], "name": name})

    op.add_column("users", sa.Column("playlist_name", sa.String(302), nullable=True))
    if values:
        connection.execute(
            users.update().where(users.c.id == sa.bindparam("user_id"))
            .values(playlist_name=sa.bindparam("name")),
            values,
        )
    normalized = sa.func.lower(users.c.playlist_name)
    collisions = connection.execute(
        sa.select(normalized).group_by(normalized).having(sa.func.count() > 1)
    ).scalars().all()
    if collisions:
        conflicts = connection.execute(
            sa.select(users.c.id, users.c.playlist_name).where(normalized.in_(collisions))
            .order_by(users.c.id)
        ).all()
        raise RuntimeError(f"Conflicting playlist names (user ID, name): {conflicts!r}")

    op.alter_column("users", "playlist_name", existing_type=sa.String(302), nullable=False)
    op.create_index("uq_users_playlist_name_lower", "users", [normalized], unique=True)


def downgrade() -> None:
    op.drop_index("uq_users_playlist_name_lower", table_name="users")
    op.drop_column("users", "playlist_name")
