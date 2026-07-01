import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.auth_service import AuthServiceClient, AuthTokenCreate, AuthTokenUpdate
from app.exceptions import AuthServiceError, AuthServiceNotFoundError
from app.models import Channel, User, UserStatus, tariff_packages, user_packages, user_tariffs
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


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
        if left.tzinfo is None or right.tzinfo is None:
            return left.replace(tzinfo=None) == right.replace(tzinfo=None)
        return left == right

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
        for user_id in dict.fromkeys(user_ids):
            user = await self.user_service.get_by_id(user_id)
            await self.sync_user_update(user)

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
        await self.user_service.set_auth_token_id(user.id, auth_token_id)
        logger.info("Synced user %d to Auth Service with token_id %d", user.id, auth_token_id)

    async def _do_recreate(self, client: AuthServiceClient, user: User) -> None:
        """Recreate the Auth Service token using the existing playlist token value."""
        deleted_ids: set[int] = set()
        if user.auth_token_id is not None:
            await client.delete_token(user.auth_token_id)
            deleted_ids.add(user.auth_token_id)

        existing_token = await client.find_token_by_value(user.token)
        if existing_token is not None:
            existing_token_id = existing_token.get("id")
            if isinstance(existing_token_id, int) and existing_token_id not in deleted_ids:
                logger.warning(
                    "Auth token for user %d exists with stale token_id %d; deleting before recreate",
                    user.id,
                    existing_token_id,
                )
                await client.delete_token(existing_token_id)

        await self._do_create(client, user)

    async def sync_user_create(self, user: User) -> None:
        """
        Sync new user to Auth Service.
        Creates token and stores auth_token_id.
        Failures are logged but don't prevent user creation.
        """
        try:
            async with AuthServiceClient() as client:
                await self._do_create(client, user)
        except AuthServiceError as e:
            logger.warning("Failed to sync user %d to Auth Service: %s", user.id, e)

    async def sync_user_update(self, user: User, *, recreate_token: bool = False) -> None:
        """
        Sync user updates to Auth Service.
        Updates token with new settings and allowed streams.
        Recreates the Auth Service token when fields unsupported by the update
        endpoint need to be replaced, while keeping the playlist token stable.
        Failures are logged but don't prevent user update.
        """
        try:
            async with AuthServiceClient() as client:
                if user.auth_token_id is None:
                    await self._do_recreate(client, user)
                    return

                if recreate_token:
                    await self._do_recreate(client, user)
                    logger.info("Recreated user %d token in Auth Service", user.id)
                    return

                action = await self._sync_user_verified(client, user)
                logger.info("Auth sync for user %d completed with action %s", user.id, action)
        except AuthServiceError as e:
            logger.warning("Failed to sync user %d update to Auth Service: %s", user.id, e)

    async def sync_user_delete(self, user: User) -> None:
        """
        Remove user token from Auth Service.
        Failures are logged but don't prevent user deletion.
        """
        try:
            if user.auth_token_id is not None:
                async with AuthServiceClient() as client:
                    await client.delete_token(user.auth_token_id)
                logger.info("Deleted user %d from Auth Service", user.id)
        except AuthServiceError as e:
            logger.warning("Failed to delete user %d from Auth Service: %s", user.id, e)

    async def sync_token_regenerate(self, user: User) -> None:
        """
        Handle token regeneration.
        Deletes old token and creates new one.
        Failures are logged but don't prevent token regeneration.
        """
        try:
            async with AuthServiceClient() as client:
                await self._do_recreate(client, user)
            logger.info("Regenerated token for user %d in Auth Service", user.id)
        except AuthServiceError as e:
            logger.warning("Failed to regenerate token for user %d in Auth Service: %s", user.id, e)

    async def sync_all_users(self) -> dict[str, int]:
        """Resync all Playlist users to Auth Service and return summary counts."""
        result = await self.db.execute(select(User).order_by(User.id))
        users = list(result.scalars().all())
        summary = {
            "total": len(users),
            "patched": 0,
            "recreated": 0,
            "recovered": 0,
            "mismatched": 0,
            "failed": 0,
        }
        playlist_tokens = {user.token for user in users}

        async with AuthServiceClient() as client:
            for user in users:
                try:
                    action = await self._sync_user_verified(
                        client,
                        user,
                        playlist_tokens=playlist_tokens,
                    )
                    summary[action] += 1
                except AuthServiceError as e:
                    logger.warning("Failed full auth resync for user %d: %s", user.id, e)
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

        if user.auth_token_id is not None:
            try:
                auth_token = await client.get_token(user.auth_token_id)
            except AuthServiceNotFoundError:
                await self._do_recreate(client, user)
                return "recreated"

            token_value = auth_token.get("token")
            auth_user_id = auth_token.get("user_id")
            if token_value != user.token:
                stale_auth_token_id = user.auth_token_id
                logger.warning(
                    "Auth token_id %d for user %d points to a different token; recovering by token value",
                    stale_auth_token_id,
                    user.id,
                )
                existing_token = await client.find_token_by_value(user.token)
                if existing_token is not None:
                    existing_token_id = existing_token.get("id")
                    if isinstance(existing_token_id, int):
                        await client.delete_token(existing_token_id)
                await self._do_create(client, user)
                if playlist_tokens is not None and token_value not in playlist_tokens:
                    await client.delete_token(stale_auth_token_id)
                return "recovered"

            if auth_user_id != expected_user_id:
                logger.warning(
                    "Auth token_id %d for user %d has user_id %r; recreating with %r",
                    user.auth_token_id,
                    user.id,
                    auth_user_id,
                    expected_user_id,
                )
                await self._do_recreate(client, user)
                return "mismatched"

            if user.valid_until is None and auth_token.get("valid_until") is not None:
                logger.info(
                    "Auth token_id %d for user %d has valid_until but Playlist user does not; recreating",
                    user.auth_token_id,
                    user.id,
                )
                await self._do_recreate(client, user)
                return "recreated"

            auth_valid_from = self._parse_auth_datetime(auth_token.get("valid_from"))
            if user.valid_from is not None and not self._datetimes_match(user.valid_from, auth_valid_from):
                logger.info(
                    "Auth token_id %d for user %d has different valid_from; recreating",
                    user.auth_token_id,
                    user.id,
                )
                await self._do_recreate(client, user)
                return "recreated"
        else:
            await self._do_recreate(client, user)
            return "recreated"

        channels = await self.user_service.resolve_channels(user.id)
        data = AuthTokenUpdate(
            status=self._map_status(user.status),
            max_sessions=user.max_sessions,
            valid_until=user.valid_until,
            allowed_streams=self._build_allowed_streams(channels),
        )
        try:
            await client.update_token(user.auth_token_id, data)
        except AuthServiceNotFoundError:
            await self._do_recreate(client, user)
            return "recreated"

        return "patched"
