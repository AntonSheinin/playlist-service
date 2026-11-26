from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.portal import PortalClient, PortalSnapshot
from app.config import get_settings
from app.exceptions import AuthServiceError, PortalSyncError, PortalUnavailableError, StreamProviderError
from app.models import User
from app.services import auth_locks
from app.services.auth_sync import AuthSyncService
from app.services.playlist_service import PlaylistService
from app.services.user_service import UserService


class PortalSyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sync(self, user_id: int) -> User:
        if not get_settings().portal_configured:
            raise PortalUnavailableError()

        async with auth_locks.auth_account_lock(user_id):
            user = await UserService(self.db).get_by_id(user_id)
            if user.portal_synced:
                user.portal_synced = False
                await self.db.commit()
            await self.push(user)
            await self.db.refresh(user, ["updated_at"])
            return user

    async def push(self, user: User) -> None:
        """Send a committed snapshot while the caller holds the account lock."""
        if user.portal_allowed and not user.auth_synced:
            try:
                registered = await AuthSyncService(self.db).has_registered_token(user)
            except AuthServiceError:
                raise PortalSyncError("Could not verify the playback token with Auth Service") from None
            if not registered:
                raise PortalSyncError("Sync Auth before sending this account's playlist to Portal")

        await PortalClient().upsert(await self.snapshot(user))
        user.portal_synced = True
        await self.db.commit()

    async def snapshot(self, user: User) -> PortalSnapshot:
        playlist = None
        if user.portal_allowed:
            try:
                generated = await PlaylistService(self.db).generate(
                    user_id=user.id, require_absolute_urls=True
                )
                playlist = generated.content
            except (StreamProviderError, ValueError):
                raise PortalSyncError("Could not generate a playlist with absolute Portal URLs") from None

        try:
            return PortalSnapshot(
                account_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                portal_allowed=user.portal_allowed,
                max_portal_devices=user.max_portal_devices,
                playlist_m3u=playlist,
            )
        except ValidationError:
            raise PortalSyncError("Account data does not meet the Portal contract") from None
