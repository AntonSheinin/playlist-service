"""PostgreSQL checks; set PLAYLIST_TEST_POSTGRES_URL to a disposable test server."""

import os
from uuid import uuid4
from pathlib import Path

import pytest
import pytest_asyncio
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.exceptions import DuplicateEntryError
from app.models import Base
from app.services.playlist_service import PlaylistService
from app.services.user_service import UserService

pytestmark = pytest.mark.skipif(
    not os.environ.get("PLAYLIST_TEST_POSTGRES_URL"),
    reason="Requires isolated PostgreSQL test server",
)
scripts = ScriptDirectory(str(Path(__file__).resolve().parents[1] / "alembic"))
migration = scripts.get_revision("007").module


@pytest_asyncio.fixture
async def postgres_engine():
    url = os.environ["PLAYLIST_TEST_POSTGRES_URL"]
    schema = "playlist_test_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        yield engine
    finally:
        await engine.dispose()
        async with admin.begin() as connection:
            await connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


async def seed_legacy_users(engine, *, collision=False):
    async with engine.begin() as connection:
        def upgrade_legacy(conn):
            with Operations.context(MigrationContext.configure(conn)):
                for script in reversed(list(scripts.iterate_revisions("006", "base"))):
                    script.module.upgrade()

        await connection.run_sync(upgrade_legacy)
        await connection.execute(sa.text(
            "INSERT INTO users (id, first_name, last_name, agreement_number, token) "
            "VALUES (:id, :first, :last, :agreement, :token)"
        ), [
            {"id": 1, "first": "Al ice!", "last": "Иванов", "agreement": "A/123", "token": "first"},
            {"id": 2, "first": "al ice!" if collision else "Émission",
             "last": "Иванов" if collision else "French", "agreement": "A123" if collision else "2",
             "token": "second"},
        ])


def run_migration(connection, direction="upgrade"):
    with Operations.context(MigrationContext.configure(connection)):
        getattr(migration, direction)()


@pytest.mark.asyncio
async def test_postgres_migration_preserves_names_and_can_downgrade(postgres_engine):
    await seed_legacy_users(postgres_engine)
    async with postgres_engine.begin() as connection:
        await connection.run_sync(run_migration)
        names = (await connection.execute(sa.text(
            "SELECT playlist_name FROM users ORDER BY id"
        ))).scalars().all()
        assert names == ["Иванов_Al_ice_A123", "French_Émission_2"]
        column = await connection.run_sync(
            lambda conn: next(c for c in sa.inspect(conn).get_columns("users") if c["name"] == "playlist_name")
        )
        assert column["nullable"] is False
        assert column["type"].length == 302
        indexes = await connection.run_sync(lambda conn: sa.inspect(conn).get_indexes("users"))
        assert any(i["name"] == "uq_users_playlist_name_lower" and i["unique"] for i in indexes)
        await connection.run_sync(lambda conn: run_migration(conn, "downgrade"))
        columns = await connection.run_sync(lambda conn: sa.inspect(conn).get_columns("users"))
        assert "playlist_name" not in {column["name"] for column in columns}


@pytest.mark.asyncio
async def test_postgres_collision_aborts_migration_transaction(postgres_engine):
    await seed_legacy_users(postgres_engine, collision=True)
    with pytest.raises(RuntimeError, match="Conflicting playlist names.*1.*2"):
        async with postgres_engine.begin() as connection:
            await connection.run_sync(run_migration)
    async with postgres_engine.connect() as connection:
        columns = await connection.run_sync(lambda conn: sa.inspect(conn).get_columns("users"))
        assert "playlist_name" not in {column["name"] for column in columns}


@pytest.mark.asyncio
async def test_postgres_unicode_lookup_and_concurrent_name_conflict(postgres_engine):
    async with postgres_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    async with sessions() as session:
        first = await UserService(session).create("A", "B", "1")
        second = await UserService(session).create("C", "D", "2")
        first_id, second_id = first.id, second.id
        await session.commit()
    # Both requests pass their prechecks before either claims the name.
    async with sessions() as left, sessions() as right:
        await UserService(left)._ensure_playlist_name_available("Émission")
        await UserService(right)._ensure_playlist_name_available("émission")
        await UserService(left).update(first_id, playlist_name="Émission")
        await left.commit()
        user = await UserService(right).get_by_id(second_id)
        user.playlist_name = "émission"
        with pytest.raises(DuplicateEntryError):
            await UserService(right)._flush_user()
        await right.rollback()
        playlist = await PlaylistService(right).generate(playlist_name="ÉMISSION")
        assert playlist.filename == "Émission.m3u8"
        saved = await PlaylistService(right).generate(user_id=second_id)
        assert saved.filename == "D_C_2.m3u8"
