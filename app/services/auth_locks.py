import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.pool import NullPool

from app.exceptions import NotFoundError, PlaylistServiceError
from app.services.database import engine

# Session locks span business commits. Dedicated connections keep lock waiters
# from exhausting the application's transaction pool.
lock_engine = create_async_engine(engine.url, poolclass=NullPool)
_LOCK_NAMESPACE = 0x52555456
_CATALOG_KEY = 0  # Account IDs are positive.
LOCK_WAIT_SECONDS = 5


class AuthSyncBusyError(PlaylistServiceError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("Account sync is busy. Retry shortly.", code="AUTH_SYNC_BUSY")


async def _lock(
    connection: AsyncConnection, key: int, *, shared: bool = False, wait_seconds: float | None = None
) -> None:
    lock_function = "pg_advisory_lock_shared" if shared else "pg_advisory_lock"
    try:
        async with asyncio.timeout(LOCK_WAIT_SECONDS if wait_seconds is None else wait_seconds):
            await connection.execute(
                text(f"SELECT {lock_function}(:namespace, :key)"),
                {"namespace": _LOCK_NAMESPACE, "key": key},
            )
            await connection.commit()
    except TimeoutError as error:
        raise AuthSyncBusyError() from error


@asynccontextmanager
async def auth_catalog_lock(
    *, shared: bool = False
) -> AsyncIterator[AsyncConnection]:
    """Catalog changes take the exclusive lock to update many accounts together."""
    async with lock_engine.connect() as connection:
        await _lock(connection, _CATALOG_KEY, shared=shared)
        # Closing the unpooled connection releases all its session locks.
        yield connection


@asynccontextmanager
async def auth_account_lock(
    user_id: int, *, wait_seconds: float | None = None
) -> AsyncIterator[None]:
    if not 1 <= user_id <= 2_147_483_647:
        raise NotFoundError("User not found")
    async with lock_engine.connect() as connection:
        await _lock(connection, user_id, wait_seconds=wait_seconds)
        yield


async def try_catalog_account_locks(
    connection: AsyncConnection, user_ids: list[int]
) -> int | None:
    """Report a busy account without waiting under the exclusive catalog lock."""
    if not user_ids:
        return None
    return await connection.scalar(
        text(
            "SELECT id FROM unnest(CAST(:user_ids AS integer[])) AS accounts(id) "
            "WHERE NOT pg_try_advisory_lock(:namespace, id) LIMIT 1"
        ),
        {"namespace": _LOCK_NAMESPACE, "user_ids": sorted(set(user_ids))},
    )
