from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import PlaylistServiceError, ValidationError
from app.models import User
from app.services import auth_locks
from app.services.user_service import UserService


class PortalUnavailableError(PlaylistServiceError):
    status_code = 503

    def __init__(self) -> None:
        super().__init__("Proxy Portal integration is unavailable", code="PORTAL_SYNC_UNAVAILABLE")


class PortalSyncError(PlaylistServiceError):
    status_code = 502

    def __init__(self) -> None:
        super().__init__("Mock Proxy Portal sync failed", code="PORTAL_SYNC_ERROR")


class PortalSyncService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sync(self, user_id: int) -> User:
        mock_result = get_settings().active_portal_mock
        if mock_result is None:
            raise PortalUnavailableError()

        async with auth_locks.auth_account_lock(user_id):
            user = await UserService(self.db).get_by_id(user_id)
            if not user.portal_allowed:
                raise ValidationError("Allow portal access before syncing this account")
            if not user.portal_synced:
                if mock_result == "failure":
                    raise PortalSyncError()
                user.portal_synced = True
                await self.db.commit()
                await self.db.refresh(user, ["updated_at"])
            return user
