import logging
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack, nullcontext
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.portal import PortalClient
from app.config import get_settings
from app.exceptions import PortalSyncError, ValidationError
from app.models import User
from app.schemas import UserCreate, UserResponse, UserSaveResponse, UserUpdate
from app.services import auth_locks
from app.services.auth_sync import AuthSyncService
from app.services.portal_sync import PortalSyncService
from app.services.user_service import UserService

SyncResult = Literal["skipped", "succeeded", "failed"]
logger = logging.getLogger(__name__)


class AccountService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserService(db)
        self.auth = AuthSyncService(db)
        self.portal = PortalSyncService(db)

    async def create(self, data: UserCreate) -> UserSaveResponse:
        async with AsyncExitStack() as account:
            async with auth_locks.auth_catalog_lock(shared=True):
                user = await self.users.create(**data.model_dump())
                await account.enter_async_context(auth_locks.auth_account_lock(user.id))
                await self.db.commit()
            await self.auth.sync_user_create(user)
            await self.db.commit()
            portal_result = await self._sync_portal_after_save(user)
            return await self._sync_response(user, portal_result=portal_result)

    async def update(self, user_id: int, data: UserUpdate) -> UserSaveResponse:
        async with auth_locks.auth_account_lock(user_id):
            assignments_changed = any(
                ids is not None for ids in (data.tariff_ids, data.package_ids, data.channel_ids)
            )
            catalog = auth_locks.auth_catalog_lock(shared=True) if assignments_changed else nullcontext()
            async with catalog:
                user = await self.users.get_by_id(user_id)
                before = (user.status, user.max_sessions, user.valid_from, user.valid_until)
                portal_before = self._portal_inputs(user)
                streams_before = None
                if assignments_changed:
                    streams_before = (await self.auth.allowed_streams_for_users([user_id]))[user_id]

                user = await self.users.update(user_id, **data.model_dump())
                if user.valid_from is not None and user.valid_until is not None:
                    if user.valid_until <= user.valid_from:
                        raise ValidationError("Valid until must be after valid from")

                after = (user.status, user.max_sessions, user.valid_from, user.valid_until)
                auth_changed = before != after
                if streams_before is not None and not auth_changed:
                    streams_after = (await self.auth.allowed_streams_for_users([user_id]))[user_id]
                    auth_changed = streams_before != streams_after
                if auth_changed:
                    user.auth_synced = False
                portal_changed = portal_before != self._portal_inputs(user)
                if portal_changed:
                    user.portal_synced = False
                await self.db.commit()
            if auth_changed:
                await self.auth.sync_user_update(user)
                await self.db.commit()
            portal_result = await self._sync_portal_after_save(user) if portal_changed else "skipped"
            return await self._sync_response(user, attempted=auth_changed, portal_result=portal_result)

    async def strict_auth_update(
        self, user_id: int, update: Callable[[UserService], Awaitable[User]]
    ) -> User:
        async with auth_locks.auth_account_lock(user_id):
            user = await self.users.get_by_id(user_id)
            user.auth_synced = False
            await self.db.commit()
            async with self.db.begin():
                user = await update(self.users)
                await self.auth.sync_user_update(user, strict=True)
            return user

    async def retry_auth(self, user_id: int) -> User:
        async with auth_locks.auth_account_lock(user_id):
            user = await self.users.get_by_id(user_id)
            if not user.auth_synced:
                await self.auth.sync_user_update(user, strict=True)
                await self.db.commit()
                await self.db.refresh(user, ["updated_at"])
            return user

    async def regenerate_token(self, user_id: int) -> UserSaveResponse:
        async with auth_locks.auth_account_lock(user_id):
            user = await self.users.get_by_id(user_id)
            if user.auth_previous_token is not None:
                # Keep the earlier token trace until its revocation is confirmed.
                await self.auth.sync_user_update(user, strict=True)
                await self.db.commit()
            user = await self.users.regenerate_token(user_id)
            if user.portal_allowed:
                user.portal_synced = False
            await self.db.commit()
            await self.auth.sync_user_update(user)
            await self.db.commit()
            portal_result = "skipped"
            if user.portal_allowed and get_settings().portal_configured:
                portal_result = await self._sync_portal_after_save(user) if user.auth_synced else "failed"
            return await self._sync_response(user, portal_result=portal_result)

    async def delete(self, user_id: int) -> None:
        async with auth_locks.auth_account_lock(user_id):
            user = await self.users.get_by_id(user_id)
            user.auth_synced = False
            await self.db.commit()
            await self.auth.sync_user_delete(user)
            if get_settings().portal_configured:
                user.portal_synced = False
                await self.db.commit()
                await PortalClient().delete(user.id)
            async with auth_locks.auth_catalog_lock(shared=True):
                await self.users.delete(user_id)
                await self.db.commit()

    @staticmethod
    def _portal_inputs(user: User) -> tuple[object, ...]:
        return (
            user.first_name,
            user.last_name,
            user.portal_allowed,
            user.max_portal_devices,
            frozenset(tariff.id for tariff in user.tariffs),
            frozenset(package.id for package in user.packages),
            frozenset(channel.id for channel in user.channels),
        )

    async def _sync_portal_after_save(self, user: User) -> SyncResult:
        if not get_settings().portal_configured:
            return "skipped"
        try:
            await self.portal.push(user)
        except PortalSyncError as error:
            logger.warning("Portal sync failed for account %d: %s", user.id, error.message)
            return "failed"
        return "succeeded"

    async def _sync_response(
        self, user: User, *, portal_result: SyncResult, attempted: bool = True
    ) -> UserSaveResponse:
        await self.db.refresh(user, ["updated_at"])
        outcome: SyncResult = "skipped"
        if attempted:
            outcome = "succeeded" if user.auth_synced else "failed"
        return UserSaveResponse(
            **UserResponse.model_validate(user).model_dump(),
            auth_sync_result=outcome,
            portal_sync_result=portal_result,
        )
