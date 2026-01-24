import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.auth_service import AuthServiceClient, AuthTokenCreate, AuthTokenUpdate
from app.exceptions import AuthServiceError
from app.models import User, UserStatus
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

    async def _do_create(self, client: AuthServiceClient, user: User) -> None:
        """Create token in Auth Service and store auth_token_id."""
        channels = await self.user_service.resolve_channels(user.id)
        allowed_streams = [ch.stream_name for ch in channels]

        data = AuthTokenCreate(
            token=user.token,
            user_id=user.agreement_number,
            status=self._map_status(user.status),
            max_sessions=user.max_sessions,
            valid_from=user.valid_from,
            valid_until=user.valid_until,
            allowed_streams=allowed_streams,
            meta={
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        )

        auth_token_id = await client.create_token(data)
        await self.user_service.set_auth_token_id(user.id, auth_token_id)
        logger.info("Synced user %d to Auth Service with token_id %d", user.id, auth_token_id)

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

    async def sync_user_update(self, user: User) -> None:
        """
        Sync user updates to Auth Service.
        Updates token with new settings and allowed streams.
        Failures are logged but don't prevent user update.
        """
        try:
            async with AuthServiceClient() as client:
                if user.auth_token_id is None:
                    await self._do_create(client, user)
                    return

                channels = await self.user_service.resolve_channels(user.id)
                allowed_streams = [ch.stream_name for ch in channels]

                data = AuthTokenUpdate(
                    status=self._map_status(user.status),
                    max_sessions=user.max_sessions,
                    valid_from=user.valid_from,
                    valid_until=user.valid_until,
                    allowed_streams=allowed_streams,
                    meta={
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                    },
                )

                await client.update_token(user.auth_token_id, data)
                logger.info("Updated user %d in Auth Service", user.id)
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
                if user.auth_token_id is not None:
                    await client.delete_token(user.auth_token_id)
                await self._do_create(client, user)
            logger.info("Regenerated token for user %d in Auth Service", user.id)
        except AuthServiceError as e:
            logger.warning("Failed to regenerate token for user %d in Auth Service: %s", user.id, e)
