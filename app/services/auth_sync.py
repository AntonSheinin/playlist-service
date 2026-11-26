import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import monotonic
from typing import Any, TypeVar

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.auth_service import AuthServiceClient, AuthTokenCreate, AuthTokenUpdate
from app.exceptions import AuthServiceError, AuthServiceNotFoundError, NotFoundError
from app.models import Channel, User, UserStatus, tariff_packages, user_packages, user_tariffs
from app.services import auth_locks
from app.services.user_service import UserService, user_channel_assignments

logger = logging.getLogger(__name__)
T = TypeVar("T")


class AuthSyncService:
    """Service for synchronizing user tokens with Auth Service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_service = UserService(db)

    def _map_status(self, status: UserStatus) -> str:
        """Map internal status to Auth Service status."""
        return "active" if status == UserStatus.ENABLED else "suspended"

    def _build_allowed_streams(self, channels: list[Channel]) -> list[str]:
        """Build provider-agnostic allowed stream names without duplicates."""
        return list(dict.fromkeys(ch.stream_name for ch in channels))

    def _parse_auth_datetime(self, value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _datetimes_match(self, left: datetime | None, right: datetime | None) -> bool:
        if left is None or right is None:
            return left is right
        if left.utcoffset() is None:
            left = left.replace(tzinfo=UTC)
        if right.utcoffset() is None:
            right = right.replace(tzinfo=UTC)
        return left.astimezone(UTC) == right.astimezone(UTC)

    async def get_user_ids_for_packages(self, package_ids: list[int]) -> list[int]:
        """Find users whose resolved channels can change when packages change."""
        if not package_ids:
            return []

        direct_users = select(user_packages.c.user_id).where(
            user_packages.c.package_id.in_(package_ids)
        )
        tariff_users = (
            select(user_tariffs.c.user_id)
            .join(tariff_packages, tariff_packages.c.tariff_id == user_tariffs.c.tariff_id)
            .where(tariff_packages.c.package_id.in_(package_ids))
        )
        stmt = direct_users.union(tariff_users)
        result = await self.db.execute(stmt)
        return sorted(set(result.scalars().all()))

    async def get_user_ids_for_tariffs(self, tariff_ids: list[int]) -> list[int]:
        """Find users whose resolved channels can change when tariffs change."""
        if not tariff_ids:
            return []

        stmt = (
            select(user_tariffs.c.user_id)
            .where(user_tariffs.c.tariff_id.in_(tariff_ids))
            .distinct()
        )
        result = await self.db.execute(stmt)
        return sorted(result.scalars().all())

    async def sync_users_by_ids(self, user_ids: list[int]) -> None:
        """Refresh Auth Service tokens for all provided user IDs."""
        for user_id in sorted(set(user_ids)):
            try:
                async with auth_locks.auth_account_lock(user_id):
                    try:
                        user = await self.user_service.get_by_id(user_id)
                    except NotFoundError:
                        await self.db.rollback()
                        continue
                    if not user.auth_synced:
                        await self.sync_user_update(user)
                    await self.db.commit()
            except auth_locks.AuthSyncBusyError:
                logger.warning("Deferred Auth sync for busy account %d", user_id)

    async def get_user_ids_for_channel(self, channel_id: int) -> list[int]:
        assignments = user_channel_assignments().subquery()
        result = await self.db.scalars(
            select(assignments.c.user_id).where(assignments.c.channel_id == channel_id)
        )
        return list(result)

    async def allowed_streams_for_users(self, user_ids: list[int]) -> dict[int, set[str]]:
        streams: dict[int, set[str]] = {user_id: set() for user_id in user_ids}
        if user_ids:
            assignments = user_channel_assignments(user_ids).subquery()
            rows = await self.db.execute(
                select(assignments.c.user_id, Channel.stream_name)
                .select_from(assignments)
                .join(Channel, Channel.id == assignments.c.channel_id)
                .distinct()
            )
            for user_id, stream_name in rows:
                streams[user_id].add(stream_name)
        return streams

    async def apply_catalog_change(
        self,
        affected_users: Callable[[], Awaitable[list[int]]],
        change: Callable[[], Awaitable[T]],
    ) -> T:
        """Commit catalog changes and their invalidations before pushing to Auth."""
        deadline = monotonic() + auth_locks.LOCK_WAIT_SECONDS
        while True:
            async with auth_locks.auth_catalog_lock() as connection:
                user_ids = await affected_users()
                busy_user = await auth_locks.try_catalog_account_locks(connection, user_ids)
                if busy_user is None:
                    before = await self.allowed_streams_for_users(user_ids)
                    result = await change()
                    after = await self.allowed_streams_for_users(user_ids)
                    changed = [user_id for user_id in before if before[user_id] != after[user_id]]
                    if changed:
                        await self.db.execute(
                            update(User).where(User.id.in_(changed)).values(auth_synced=False)
                        )
                    await self.db.commit()
                    break
                await self.db.rollback()
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise auth_locks.AuthSyncBusyError()
            # Recompute recipients after waiting because their assignments may change.
            async with auth_locks.auth_account_lock(busy_user, wait_seconds=remaining):
                pass
        await self.sync_users_by_ids(changed)
        return result

    async def _do_create(self, client: AuthServiceClient, user: User) -> None:
        """Create token in Auth Service and store auth_token_id."""
        channels = await self.user_service.resolve_channels(user.id)
        allowed_streams = self._build_allowed_streams(channels)

        data = AuthTokenCreate(
            token=user.token,
            user_id=str(user.id),
            status=self._map_status(user.status),
            max_sessions=user.max_sessions,
            valid_from=user.valid_from,
            valid_until=user.valid_until,
            allowed_streams=allowed_streams,
        )

        auth_token_id = await client.create_token(data)
        user.auth_token_id = auth_token_id
        logger.info("Synced user %d to Auth Service with token_id %d", user.id, auth_token_id)

    async def _do_recreate(
        self, client: AuthServiceClient, user: User, *, verified_id: int | None = None
    ) -> None:
        """Recreate the Auth Service token using the existing playlist token value."""
        if verified_id is None:
            existing_token = await client.find_token_by_value(user.token)
            if existing_token is not None:
                verified_id = self._verified_token_id(existing_token, user.token)
        if verified_id is not None:
            await client.delete_token(verified_id)

        await self._do_create(client, user)

    @staticmethod
    def _verified_token_id(record: dict[str, Any], expected_token: str) -> int:
        token_id = record.get("id")
        if type(token_id) is not int or token_id <= 0 or record.get("token") != expected_token:
            raise AuthServiceError("Could not verify Auth Service token ownership")
        return token_id

    async def _delete_token_by_value(
        self, client: AuthServiceClient, token: str, auth_token_id: int | None
    ) -> int | None:
        record = None
        if auth_token_id is not None:
            try:
                record = await client.get_token(auth_token_id)
            except AuthServiceNotFoundError:
                pass
        if record is None or record.get("token") != token:
            record = await client.find_token_by_value(token)
        if record is None:
            return None
        token_id = self._verified_token_id(record, token)
        await client.delete_token(token_id)
        return token_id

    async def sync_user_create(self, user: User) -> None:
        """
        Sync new user to Auth Service.
        Creates token and stores auth_token_id.
        Failures are logged but don't prevent user creation.
        """
        user.auth_synced = False
        try:
            async with AuthServiceClient() as client:
                await self._do_create(client, user)
        except AuthServiceError:
            logger.warning("Failed to sync new user %d to Auth Service", user.id)
        else:
            user.auth_synced = True

    async def sync_user_update(
        self,
        user: User,
        *,
        strict: bool = False,
    ) -> None:
        """
        Sync user updates to Auth Service.
        Updates token with new settings and allowed streams.
        Recreates the Auth Service token when fields unsupported by the update
        endpoint need to be replaced, while keeping the playlist token stable.
        Failures are logged but don't prevent user update unless strict=True.
        """
        user.auth_synced = False
        try:
            async with AuthServiceClient() as client:
                action = await self._sync_user_verified(client, user)
                logger.info("Auth sync for user %d completed with action %s", user.id, action)
        except AuthServiceError:
            logger.warning("Failed to sync user %d update to Auth Service", user.id)
            if strict:
                raise
        else:
            user.auth_synced = True

    async def sync_user_delete(self, user: User) -> None:
        """Revoke every known token before the middleware removes the account."""
        failure = None
        async with AuthServiceClient() as client:
            for token in (user.token, user.auth_previous_token):
                if token is None:
                    continue
                try:
                    await self._delete_token_by_value(client, token, user.auth_token_id)
                except AuthServiceError as error:
                    failure = error
                    logger.warning("Could not revoke an Auth token for user %d", user.id)
        if failure is not None:
            raise AuthServiceError("Account retained because Auth token revocation failed") from failure

    async def has_registered_token(self, user: User) -> bool:
        async with AuthServiceClient() as client:
            if user.auth_token_id is not None:
                try:
                    record = await client.get_token(user.auth_token_id)
                except AuthServiceNotFoundError:
                    pass
                else:
                    if record.get("token") == user.token:
                        return record.get("user_id") == str(user.id)
            record = await client.find_token_by_value(user.token)
            return record is not None and record.get("user_id") == str(user.id)

    async def sync_all_users(self) -> dict[str, int]:
        """Resync all Playlist users to Auth Service and return summary counts."""
        accounts = (
            await self.db.execute(select(User.id, User.token, User.auth_previous_token).order_by(User.id))
        ).all()
        await self.db.commit()
        summary = {
            "total": len(accounts),
            "patched": 0,
            "recreated": 0,
            "recovered": 0,
            "mismatched": 0,
            "failed": 0,
        }
        playlist_tokens = {
            token for _, current, previous in accounts for token in (current, previous) if token is not None
        }

        async with AuthServiceClient() as client:
            for user_id, _, _ in accounts:
                try:
                    async with auth_locks.auth_account_lock(user_id):
                        user = await self.user_service.get_by_id(user_id)
                        user.auth_synced = False
                        await self.db.commit()
                        async with self.db.begin():
                            action = await self._sync_user_verified(
                                client, user, playlist_tokens=playlist_tokens
                            )
                            user.auth_synced = True
                        summary[action] += 1
                except NotFoundError:
                    await self.db.rollback()
                    summary["total"] -= 1
                except (AuthServiceError, auth_locks.AuthSyncBusyError):
                    logger.warning("Failed full Auth resync for user %d", user_id)
                    summary["failed"] += 1

        return summary

    async def _sync_user_verified(
        self,
        client: AuthServiceClient,
        user: User,
        *,
        playlist_tokens: set[str] | None = None,
    ) -> str:
        """Patch a verified Auth token or recreate/recover when ownership is stale."""
        expected_user_id = str(user.id)
        if user.auth_previous_token is not None:
            deleted_id = await self._delete_token_by_value(
                client, user.auth_previous_token, user.auth_token_id
            )
            if deleted_id is not None and deleted_id == user.auth_token_id:
                user.auth_token_id = None
            user.auth_previous_token = None

        auth_token = None
        if user.auth_token_id is not None:
            try:
                auth_token = await client.get_token(user.auth_token_id)
            except AuthServiceNotFoundError:
                pass

        if auth_token is not None:
            token_value = auth_token.get("token")
            auth_user_id = auth_token.get("user_id")
            if token_value != user.token:
                stale_auth_token_id = user.auth_token_id
                logger.warning(
                    "Auth token_id %d for user %d points to a different token; recovering by token value",
                    stale_auth_token_id,
                    user.id,
                )
                await self._do_recreate(client, user)
                if (
                    playlist_tokens is not None
                    and auth_token.get("id") == stale_auth_token_id
                    and token_value not in playlist_tokens
                    and auth_user_id == expected_user_id
                ):
                    await client.delete_token(stale_auth_token_id)
                return "recovered"
        else:
            # A timed-out create may have succeeded without recording its ID locally.
            auth_token = await client.find_token_by_value(user.token)
            if auth_token is None:
                await self._do_create(client, user)
                return "recreated"
            user.auth_token_id = self._verified_token_id(auth_token, user.token)

        auth_token_id = self._verified_token_id(auth_token, user.token)
        if auth_token_id != user.auth_token_id:
            raise AuthServiceError("Auth Service returned an unexpected token ID")

        if auth_token.get("user_id") != expected_user_id:
            await self._do_recreate(client, user, verified_id=auth_token_id)
            return "mismatched"

        auth_valid_from = self._parse_auth_datetime(auth_token.get("valid_from"))
        if (
            not self._datetimes_match(user.valid_from, auth_valid_from)
            or (user.valid_from is None and auth_token.get("valid_from") is not None)
            or (user.valid_until is None and auth_token.get("valid_until") is not None)
        ):
            await self._do_recreate(client, user, verified_id=auth_token_id)
            return "recreated"

        channels = await self.user_service.resolve_channels(user.id)
        data = AuthTokenUpdate(
            status=self._map_status(user.status),
            max_sessions=user.max_sessions,
            valid_until=user.valid_until,
            allowed_streams=self._build_allowed_streams(channels),
        )
        try:
            await client.update_token(auth_token_id, data)
        except AuthServiceNotFoundError:
            await self._do_recreate(client, user)
            return "recreated"

        return "patched"
