"""PostgreSQL checks; set PLAYLIST_TEST_POSTGRES_URL to a disposable test server."""

import asyncio
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
from sqlalchemy.pool import NullPool

from app.exceptions import DuplicateEntryError, NotFoundError
from app.models import Base, User
from app.schemas import UserUpdate
from app.services import auth_locks
from app.services.account_service import AccountService
from app.services.auth_sync import AuthSyncService
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


@pytest.mark.asyncio
async def test_account_sync_migration_defaults_existing_accounts_to_unconfirmed(postgres_engine):
    await seed_legacy_users(postgres_engine)
    account_sync_migration = scripts.get_revision("008").module
    portal_devices_migration = scripts.get_revision("009").module

    def migrate(conn, revision, direction):
        with Operations.context(MigrationContext.configure(conn)):
            getattr(revision, direction)()

    async with postgres_engine.begin() as conn:
        await conn.run_sync(run_migration)
        await conn.run_sync(migrate, account_sync_migration, "upgrade")
        await conn.execute(sa.text(
            "UPDATE users SET portal_allowed = TRUE, portal_synced = TRUE, auth_synced = TRUE WHERE id = 1"
        ))
        await conn.run_sync(migrate, portal_devices_migration, "upgrade")
        rows = (await conn.execute(sa.text(
            "SELECT auth_synced, portal_synced, auth_previous_token, max_portal_devices "
            "FROM users ORDER BY id"
        ))).all()
        assert rows == [(True, False, None, 1), (False, False, None, 1)]
        with pytest.raises(sa.exc.IntegrityError, match="ck_users_max_portal_devices_positive"):
            async with conn.begin_nested():
                await conn.execute(sa.text("UPDATE users SET max_portal_devices = 0 WHERE id = 1"))
        await conn.run_sync(migrate, portal_devices_migration, "downgrade")
        await conn.run_sync(migrate, account_sync_migration, "downgrade")
        columns = await conn.run_sync(lambda c: sa.inspect(c).get_columns("users"))
        assert {"auth_synced", "portal_synced", "auth_previous_token", "max_portal_devices"}.isdisjoint(
            column["name"] for column in columns
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("second_action", ["update", "delete"])
async def test_account_sync_serializes_retry_with_save_or_delete(
    postgres_engine, monkeypatch, second_action,
):
    lock_engine = create_async_engine(postgres_engine.url, poolclass=NullPool)
    monkeypatch.setattr(auth_locks, "lock_engine", lock_engine)
    async with postgres_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    async with sessions() as session:
        user = await UserService(session).create("A", "B", "1")
        user.auth_token_id = 10
        user_id, token = user.id, user.token
        await session.commit()

    first_write = asyncio.Event()
    release = asyncio.Event()
    writes = []

    class AuthClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get_token(self, token_id):
            return {"id": token_id, "token": token, "user_id": str(user_id)}

        async def update_token(self, token_id, payload):
            writes.append(payload.max_sessions)
            if len(writes) == 1:
                first_write.set()
                await release.wait()

        async def delete_token(self, token_id):
            writes.append("deleted")

    monkeypatch.setattr("app.services.auth_sync.AuthServiceClient", AuthClient)

    async def wait_for_account_lock_waiter():
        async with postgres_engine.connect() as query:
            while not await query.scalar(
                sa.text(
                    "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype = 'advisory' "
                    "AND classid = :namespace AND objid = :user_id AND NOT granted)"
                ),
                {"namespace": auth_locks._LOCK_NAMESPACE, "user_id": user_id},
            ):
                await asyncio.sleep(0.01)

    async with sessions() as left, sessions() as right:
        retry = asyncio.create_task(AccountService(left).retry_auth(user_id))
        try:
            await asyncio.wait_for(first_write.wait(), 5)
            service = AccountService(right)
            if second_action == "update":
                second = service.update(user_id, UserUpdate(max_sessions=3))
            else:
                second = service.delete(user_id)
            async with asyncio.TaskGroup() as tasks:
                tasks.create_task(second)
                try:
                    await asyncio.wait_for(wait_for_account_lock_waiter(), 5)
                    assert writes == [1]
                finally:
                    release.set()
            await asyncio.wait_for(retry, 5)
        finally:
            release.set()
            if not retry.done():
                retry.cancel()
                await asyncio.gather(retry, return_exceptions=True)
            await lock_engine.dispose()

    async with sessions() as session:
        saved = await session.get(User, user_id)
        if second_action == "update":
            assert writes == [1, 3]
            assert saved.auth_synced is True
            assert saved.max_sessions == 3
        else:
            assert writes == [1, "deleted"]
            assert saved is None


@pytest.mark.asyncio
async def test_catalog_wait_releases_shared_gate_and_times_out(postgres_engine, monkeypatch):
    lock_engine = create_async_engine(postgres_engine.url, poolclass=NullPool)
    monkeypatch.setattr(auth_locks, "lock_engine", lock_engine)
    monkeypatch.setattr(auth_locks, "LOCK_WAIT_SECONDS", 1)
    try_locks = auth_locks.try_catalog_account_locks
    waiting = asyncio.Event()

    async def observe_busy_account(connection, user_ids):
        busy = await try_locks(connection, user_ids)
        assert busy == 1
        waiting.set()
        return busy

    monkeypatch.setattr(auth_locks, "try_catalog_account_locks", observe_busy_account)

    async def affected_users():
        return [1]

    async def change():
        pytest.fail("A catalog mutation must not run before acquiring affected account locks")

    async def unrelated_assignment_lock():
        async with auth_locks.auth_account_lock(2):
            async with auth_locks.auth_catalog_lock(shared=True):
                pass

    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    try:
        async with sessions() as db, auth_locks.auth_account_lock(1):
            async with asyncio.TaskGroup() as tasks:
                async def blocked_change():
                    with pytest.raises(auth_locks.AuthSyncBusyError):
                        await AuthSyncService(db).apply_catalog_change(affected_users, change)

                catalog = tasks.create_task(blocked_change())
                await asyncio.wait_for(waiting.wait(), 2)
                await asyncio.wait_for(unrelated_assignment_lock(), 0.8)
                assert not catalog.done()
        async with auth_locks.auth_catalog_lock() as catalog_connection:
            assert await try_locks(catalog_connection, [1, 2, 2]) is None
            async with lock_engine.connect() as contender:
                assert await try_locks(contender, [2]) == 2
        for invalid_user_id in (0, -1, 2_147_483_648):
            with pytest.raises(NotFoundError):
                async with auth_locks.auth_account_lock(invalid_user_id):
                    pytest.fail("Invalid account IDs must be rejected before locking")
    finally:
        await lock_engine.dispose()
