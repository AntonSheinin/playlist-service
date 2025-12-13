from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.dependencies import CurrentAdminId, DBSession
from app.models import UserStatus
from app.schemas.common import MessageResponse, PaginatedData, PaginatedResponse, SuccessResponse
from app.schemas.user import (
    PlaylistPreview,
    ResolvedChannel,
    UserCreate,
    UserListItem,
    UserResponse,
    UserUpdate,
)
from app.services.auth_sync import AuthSyncService
from app.services.playlist_generator import PlaylistGenerator
from app.services.user_service import UserService
from app.utils.pagination import PaginationParams

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UserListItem])
async def list_users(
    _admin_id: CurrentAdminId,
    db: DBSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = None,
    status: UserStatus | None = None,
    tariff_id: int | None = None,
) -> PaginatedResponse[UserListItem]:
    """List users with pagination and filters."""
    service = UserService(db)
    pagination = PaginationParams(page=page, per_page=per_page)

    result = await service.get_paginated(
        pagination=pagination,
        search=search,
        status=status,
        tariff_id=tariff_id,
    )

    items = []
    for user in result.items:
        item = UserListItem(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            agreement_number=user.agreement_number,
            status=user.status,
            max_sessions=user.max_sessions,
            created_at=user.created_at,
            tariffs=[{"id": t.id, "name": t.name} for t in user.tariffs],
        )
        items.append(item)

    return PaginatedResponse(
        data=PaginatedData(
            items=items,
            total=result.total,
            page=result.page,
            per_page=result.per_page,
            pages=result.pages,
        )
    )


@router.get("/{user_id}", response_model=SuccessResponse[UserResponse])
async def get_user(
    user_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[UserResponse]:
    """Get a single user by ID."""
    service = UserService(db)
    user = await service.get_by_id(user_id)
    return SuccessResponse(data=UserResponse.model_validate(user))


@router.post("", response_model=SuccessResponse[UserResponse])
async def create_user(
    data: UserCreate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[UserResponse]:
    """Create a new user and sync to Auth Service."""
    user_service = UserService(db)
    auth_sync = AuthSyncService(db)

    user = await user_service.create(
        first_name=data.first_name,
        last_name=data.last_name,
        agreement_number=data.agreement_number,
        max_sessions=data.max_sessions,
        status=data.status,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        tariff_ids=data.tariff_ids,
        package_ids=data.package_ids,
        channel_ids=data.channel_ids,
    )

    # Sync to Auth Service
    await auth_sync.sync_user_create(user)

    # Refresh user to get updated auth_token_id
    user = await user_service.get_by_id(user.id)

    return SuccessResponse(data=UserResponse.model_validate(user))


@router.patch("/{user_id}", response_model=SuccessResponse[UserResponse])
async def update_user(
    user_id: int,
    data: UserUpdate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[UserResponse]:
    """Update a user and sync to Auth Service."""
    user_service = UserService(db)
    auth_sync = AuthSyncService(db)

    user = await user_service.update(
        user_id,
        first_name=data.first_name,
        last_name=data.last_name,
        agreement_number=data.agreement_number,
        max_sessions=data.max_sessions,
        status=data.status,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        clear_valid_from=data.clear_valid_from,
        clear_valid_until=data.clear_valid_until,
        tariff_ids=data.tariff_ids,
        package_ids=data.package_ids,
        channel_ids=data.channel_ids,
    )

    # Sync to Auth Service
    await auth_sync.sync_user_update(user)

    return SuccessResponse(data=UserResponse.model_validate(user))


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> MessageResponse:
    """Delete a user and remove from Auth Service."""
    user_service = UserService(db)
    auth_sync = AuthSyncService(db)

    user = await user_service.delete(user_id)

    # Remove from Auth Service
    await auth_sync.sync_user_delete(user)

    return MessageResponse(message="User deleted successfully")


@router.post("/{user_id}/regenerate-token", response_model=SuccessResponse[UserResponse])
async def regenerate_token(
    user_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[UserResponse]:
    """Regenerate user's token and sync to Auth Service."""
    user_service = UserService(db)
    auth_sync = AuthSyncService(db)

    user = await user_service.regenerate_token(user_id)

    # Sync token regeneration to Auth Service
    await auth_sync.sync_token_regenerate(user)

    # Refresh user
    user = await user_service.get_by_id(user.id)

    return SuccessResponse(data=UserResponse.model_validate(user))


@router.get("/{user_id}/resolved-channels", response_model=SuccessResponse[list[ResolvedChannel]])
async def get_resolved_channels(
    user_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[list[ResolvedChannel]]:
    """Get resolved channel list for a user."""
    service = UserService(db)
    channels = await service.resolve_channels(user_id)

    result = [
        ResolvedChannel(
            id=ch.id,
            stream_name=ch.stream_name,
            display_name=ch.display_name,
            tvg_name=ch.tvg_name,
            group_name=ch.group.name if ch.group else None,
        )
        for ch in channels
    ]

    return SuccessResponse(data=result)


@router.get("/{user_id}/playlist")
async def download_playlist(
    user_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> PlainTextResponse:
    """Download M3U playlist file for a user."""
    user_service = UserService(db)
    generator = PlaylistGenerator()

    user = await user_service.get_by_id(user_id)
    channels = await user_service.resolve_channels(user_id)

    content = generator.generate(user, channels)
    filename = generator.get_filename(user)

    return PlainTextResponse(
        content=content,
        media_type="audio/x-mpegurl",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{user_id}/playlist/preview", response_model=SuccessResponse[PlaylistPreview])
async def preview_playlist(
    user_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[PlaylistPreview]:
    """Preview playlist content for a user."""
    user_service = UserService(db)
    generator = PlaylistGenerator()

    user = await user_service.get_by_id(user_id)
    channels = await user_service.resolve_channels(user_id)

    content = generator.generate(user, channels)
    filename = generator.get_filename(user)

    return SuccessResponse(
        data=PlaylistPreview(
            filename=filename,
            content=content,
            channel_count=len(channels),
        )
    )
