import logging
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Query

from app.clients.auth_service import AuthServiceClient
from app.dependencies import DBSession, IntegrationApiKey
from app.exceptions import AuthServiceError, NotFoundError, PlaylistServiceError
from app.models import User, UserStatus
from app.schemas import (
    IntegrationMaxSessionsUpdate,
    IntegrationUserFindResponse,
    IntegrationUserSummary,
    IntegrationValidUntilUpdate,
    SessionEntry,
    SuccessResponse,
)
from app.services.auth_sync import AuthSyncService
from app.services.user_service import UserService
from app.utils.log_mapping import map_session_log_entry

logger = logging.getLogger(__name__)

router = APIRouter()


def _user_summary(user: User) -> IntegrationUserSummary:
    return IntegrationUserSummary(
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        agreement_number=user.agreement_number,
        status=user.status,
        max_sessions=user.max_sessions,
        valid_until=user.valid_until,
    )


async def _run_strict_user_update(
    *,
    action: str,
    user_id: int,
    db: DBSession,
    update: Callable[[UserService], Awaitable[User]],
) -> SuccessResponse[IntegrationUserSummary]:
    user_service = UserService(db)
    auth_sync = AuthSyncService(db)
    try:
        user = await update(user_service)
    except PlaylistServiceError:
        logger.info(
            "Integration API write rejected",
            extra={
                "source": "integration_api",
                "action": action,
                "user_id": user_id,
                "result": "rejected",
            },
        )
        raise

    try:
        await auth_sync.sync_user_update(user, strict=True)
        refreshed_user = await user_service.get_by_id(user_id)
        logger.info(
            "Integration API write completed",
            extra={
                "source": "integration_api",
                "action": action,
                "user_id": user_id,
                "result": "success",
            },
        )
        return SuccessResponse(data=_user_summary(refreshed_user))
    except AuthServiceError:
        logger.info(
            "Integration API write failed",
            extra={
                "source": "integration_api",
                "action": action,
                "user_id": user_id,
                "result": "failure",
            },
        )
        raise
    except PlaylistServiceError:
        logger.info(
            "Integration API write failed after auth sync",
            extra={
                "source": "integration_api",
                "action": action,
                "user_id": user_id,
                "result": "failure",
            },
        )
        raise


@router.get("/users/find", response_model=SuccessResponse[IntegrationUserFindResponse])
async def find_user(
    _api_key: IntegrationApiKey,
    db: DBSession,
    q: str = Query(..., min_length=2),
) -> SuccessResponse[IntegrationUserFindResponse]:
    service = UserService(db)
    matches = await service.find_exact_for_integration(q)
    if not matches:
        raise NotFoundError("User not found")

    if len(matches) == 1:
        return SuccessResponse(
            data=IntegrationUserFindResponse(
                match_type="single",
                user=_user_summary(matches[0]),
                candidates=[],
            )
        )

    return SuccessResponse(
        data=IntegrationUserFindResponse(
            match_type="candidates",
            user=None,
            candidates=[_user_summary(user) for user in matches],
        )
    )


@router.get("/users/{user_id}", response_model=SuccessResponse[IntegrationUserSummary])
async def get_user(
    user_id: int,
    _api_key: IntegrationApiKey,
    db: DBSession,
) -> SuccessResponse[IntegrationUserSummary]:
    service = UserService(db)
    user = await service.get_by_id(user_id)
    return SuccessResponse(data=_user_summary(user))


@router.post("/users/{user_id}/enable", response_model=SuccessResponse[IntegrationUserSummary])
async def enable_user(
    user_id: int,
    _api_key: IntegrationApiKey,
    db: DBSession,
) -> SuccessResponse[IntegrationUserSummary]:
    return await _run_strict_user_update(
        action="enable_user",
        user_id=user_id,
        db=db,
        update=lambda service: service.update(user_id, status=UserStatus.ENABLED),
    )


@router.post("/users/{user_id}/disable", response_model=SuccessResponse[IntegrationUserSummary])
async def disable_user(
    user_id: int,
    _api_key: IntegrationApiKey,
    db: DBSession,
) -> SuccessResponse[IntegrationUserSummary]:
    return await _run_strict_user_update(
        action="disable_user",
        user_id=user_id,
        db=db,
        update=lambda service: service.update(user_id, status=UserStatus.DISABLED),
    )


@router.put("/users/{user_id}/max-sessions", response_model=SuccessResponse[IntegrationUserSummary])
async def set_max_sessions(
    user_id: int,
    data: IntegrationMaxSessionsUpdate,
    _api_key: IntegrationApiKey,
    db: DBSession,
) -> SuccessResponse[IntegrationUserSummary]:
    return await _run_strict_user_update(
        action="set_user_max_sessions",
        user_id=user_id,
        db=db,
        update=lambda service: service.update(user_id, max_sessions=data.max_sessions),
    )


@router.put("/users/{user_id}/valid-until", response_model=SuccessResponse[IntegrationUserSummary])
async def set_valid_until(
    user_id: int,
    data: IntegrationValidUntilUpdate,
    _api_key: IntegrationApiKey,
    db: DBSession,
) -> SuccessResponse[IntegrationUserSummary]:
    return await _run_strict_user_update(
        action="set_user_valid_until",
        user_id=user_id,
        db=db,
        update=lambda service: service.update(user_id, valid_until=data.valid_until),
    )


@router.get("/users/{user_id}/sessions", response_model=SuccessResponse[list[SessionEntry]])
async def get_user_active_sessions(
    user_id: int,
    _api_key: IntegrationApiKey,
    db: DBSession,
) -> SuccessResponse[list[SessionEntry]]:
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    async with AuthServiceClient() as auth_client:
        sessions = await auth_client.get_user_sessions(
            user_id=str(user.id),
            skip=0,
            limit=100,
        )

    return SuccessResponse(
        data=[SessionEntry(**map_session_log_entry(session)) for session in sessions]
    )
