from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.auth_service import AuthServiceClient, AuthTokenCreate, AuthTokenUpdate
from app.models import User, UserStatus
from app.services.user_service import UserService


class AuthSyncService:
    """Service for synchronizing user tokens with Auth Service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.auth_client = AuthServiceClient()
        self.user_service = UserService(db)

    def _map_status(self, status: UserStatus) -> str:
        """Map internal status to Auth Service status."""
        return "active" if status == UserStatus.ENABLED else "suspended"

    async def sync_user_create(self, user: User) -> None:
        """
        Sync new user to Auth Service.
        Creates token and stores auth_token_id.
        """
        # Resolve channels for this user
        channels = await self.user_service.resolve_channels(user.id)
        allowed_streams = [ch.stream_name for ch in channels]

        # Create token in Auth Service
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

        auth_token_id = await self.auth_client.create_token(data)

        # Store auth_token_id
        await self.user_service.set_auth_token_id(user.id, auth_token_id)

    async def sync_user_update(self, user: User) -> None:
        """
        Sync user updates to Auth Service.
        Updates token with new settings and allowed streams.
        """
        if user.auth_token_id is None:
            # User not synced yet, create instead
            await self.sync_user_create(user)
            return

        # Resolve channels for this user
        channels = await self.user_service.resolve_channels(user.id)
        allowed_streams = [ch.stream_name for ch in channels]

        # Update token in Auth Service
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

        await self.auth_client.update_token(user.auth_token_id, data)

    async def sync_user_delete(self, user: User) -> None:
        """
        Remove user token from Auth Service.
        """
        if user.auth_token_id is not None:
            await self.auth_client.delete_token(user.auth_token_id)

    async def sync_token_regenerate(self, user: User) -> None:
        """
        Handle token regeneration.
        Deletes old token and creates new one.
        """
        # Delete old token if exists
        if user.auth_token_id is not None:
            await self.auth_client.delete_token(user.auth_token_id)

        # Create new token
        await self.sync_user_create(user)
