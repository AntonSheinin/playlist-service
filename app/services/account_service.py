from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack, nullcontext
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
from app.models import User
from app.schemas import UserCreate, UserResponse, UserSaveResponse, UserUpdate
from app.services import auth_locks
from app.services.auth_sync import AuthSyncService
from app.services.user_service import UserService


class AccountService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserService(db)
        self.auth = AuthSyncService(db)

    async def create(self, data: UserCreate) -> UserSaveResponse:
        async with AsyncExitStack() as account:
            async with auth_locks.auth_catalog_lock(shared=True):
                user = await self.users.create(**data.model_dump())
                await account.enter_async_context(auth_locks.auth_account_lock(user.id))
                await self.db.commit()
            await self.auth.sync_user_create(user)
            await self.db.commit()
            return await self._sync_response(user)

    async def update(self, user_id: int, data: UserUpdate) -> UserSaveResponse:
        async with auth_locks.auth_account_lock(user_id):
            assignments_changed = any(
                ids is not None for ids in (data.tariff_ids, data.package_ids, data.channel_ids)
            )
            catalog = auth_locks.auth_catalog_lock(shared=True) if assignments_changed else nullcontext()
            async with catalog:
                user = await self.users.get_by_id(user_id)
                before = (user.status, user.max_sessions, user.valid_from, user.valid_until)
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
                await self.db.commit()
            if auth_changed:
                await self.auth.sync_user_update(user)
                await self.db.commit()
            return await self._sync_response(user, attempted=auth_changed)

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
            await self.db.commit()
            await self.auth.sync_user_update(user)
            await self.db.commit()
            return await self._sync_response(user)

    async def delete(self, user_id: int) -> None:
        async with auth_locks.auth_account_lock(user_id):
            user = await self.users.get_by_id(user_id)
            user.auth_synced = False
            await self.db.commit()
            await self.auth.sync_user_delete(user)
            async with auth_locks.auth_catalog_lock(shared=True):
                await self.users.delete(user_id)
                await self.db.commit()

    async def _sync_response(self, user: User, *, attempted: bool = True) -> UserSaveResponse:
        await self.db.refresh(user, ["updated_at"])
        outcome: Literal["skipped", "succeeded", "failed"] = "skipped"
        if attempted:
            outcome = "succeeded" if user.auth_synced else "failed"
        return UserSaveResponse(
            **UserResponse.model_validate(user).model_dump(), auth_sync_result=outcome
        )
