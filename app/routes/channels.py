from fastapi import APIRouter, File, Query, UploadFile
from sqlalchemy import func, select

from app.dependencies import CurrentAdminId, DBSession
from app.exceptions import ValidationError
from app.models import Channel, StreamSource, SyncStatus
from app.schemas import (
    ChannelBulkUpdate,
    ChannelCascadeInfo,
    ChannelGroupsUpdate,
    ChannelPackagesUpdate,
    ChannelResponse,
    ChannelUpdate,
    LogoUrlRequest,
    LogoUploadResponse,
    MessageResponse,
    PaginatedData,
    PaginatedResponse,
    ReorderRequest,
    SuccessResponse,
    SyncResultResponse,
)
from app.services.channel_service import ChannelService
from app.services.auth_sync import AuthSyncService
from app.services.channel_sync import ChannelSyncService
from app.services.logo_service import is_safe_logo_path, resolve_logo_path, save_logo_file, save_logo_url
from app.utils.pagination import PaginationParams

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ChannelResponse])
async def list_channels(
    _admin_id: CurrentAdminId,
    db: DBSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = None,
    group_id: int | None = None,
    package_id: int | None = None,
    without_group: bool = False,
    without_package: bool = False,
    source: StreamSource | None = None,
    sync_status: SyncStatus | None = None,
    sort_by: str = "channel_number",
    sort_dir: str = "asc",
) -> PaginatedResponse[ChannelResponse]:
    """List channels with pagination and filters."""
    if group_id is not None and without_group:
        raise ValidationError("Choose either a group or 'without group', not both")

    if package_id is not None and without_package:
        raise ValidationError("Choose either a package or 'without package', not both")

    service = ChannelService(db)
    pagination = PaginationParams(page=page, per_page=per_page)

    result = await service.get_paginated(
        pagination=pagination,
        search=search,
        group_id=group_id,
        package_id=package_id,
        without_group=without_group,
        without_package=without_package,
        source=source,
        sync_status=sync_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    return PaginatedResponse(
        data=PaginatedData(
            items=[ChannelResponse.model_validate(ch) for ch in result.items],
            total=result.total,
            page=result.page,
            per_page=result.per_page,
            pages=result.pages,
        )
    )


@router.get("/{channel_id}", response_model=SuccessResponse[ChannelResponse])
async def get_channel(
    channel_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[ChannelResponse]:
    """Get a single channel by ID."""
    service = ChannelService(db)
    channel = await service.get_by_id(channel_id)
    return SuccessResponse(data=ChannelResponse.model_validate(channel))


@router.patch("/{channel_id}", response_model=SuccessResponse[ChannelResponse])
async def update_channel(
    channel_id: int,
    data: ChannelUpdate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[ChannelResponse]:
    """Update channel (tvg_id, tvg_logo, channel_number)."""
    service = ChannelService(db)
    channel = await service.update(
        channel_id,
        tvg_id=data.tvg_id,
        tvg_logo=data.tvg_logo,
        channel_number=data.channel_number,
    )
    return SuccessResponse(data=ChannelResponse.model_validate(channel))


@router.post("/{channel_id}/logo", response_model=SuccessResponse[LogoUploadResponse])
async def upload_channel_logo(
    channel_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
    file: UploadFile = File(...),
) -> SuccessResponse[LogoUploadResponse]:
    """Upload channel logo and return its URL."""
    service = ChannelService(db)
    channel = await service.get_by_id(channel_id)
    logo_url = await save_logo_file(file, stream_name=channel.stream_name, channel_id=channel_id)
    channel = await service.update(channel_id, tvg_logo=logo_url)
    return SuccessResponse(data=LogoUploadResponse(url=channel.tvg_logo or logo_url))


@router.post("/{channel_id}/logo-url", response_model=SuccessResponse[LogoUploadResponse])
async def upload_channel_logo_url(
    channel_id: int,
    data: LogoUrlRequest,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[LogoUploadResponse]:
    """Download channel logo from URL and return its local URL."""
    service = ChannelService(db)
    channel = await service.get_by_id(channel_id)
    logo_url = await save_logo_url(data.url, stream_name=channel.stream_name, channel_id=channel_id)
    channel = await service.update(channel_id, tvg_logo=logo_url)
    return SuccessResponse(data=LogoUploadResponse(url=channel.tvg_logo or logo_url))


@router.delete("/{channel_id}/logo", response_model=MessageResponse)
async def delete_channel_logo(
    channel_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
    delete_file: bool = Query(False, description="Delete the logo file from disk if unused"),
) -> MessageResponse:
    """Remove a channel logo, optionally deleting the local file."""
    service = ChannelService(db)
    channel = await service.get_by_id(channel_id)
    logo_url = channel.tvg_logo

    if channel.tvg_logo:
        await service.update(channel_id, tvg_logo="")

    file_deleted = False
    if delete_file and logo_url:
        logo_path = resolve_logo_path(logo_url)
        if logo_path and is_safe_logo_path(logo_path) and logo_path.exists():
            result = await db.execute(
                select(func.count(Channel.id)).where(
                    Channel.id != channel_id,
                    Channel.tvg_logo == logo_url,
                )
            )
            references = result.scalar() or 0
            if references == 0:
                logo_path.unlink()
                file_deleted = True

    if delete_file:
        message = "Logo removed and file deleted" if file_deleted else "Logo removed (file retained)"
    else:
        message = "Logo removed"

    return MessageResponse(message=message)


@router.patch("", response_model=MessageResponse)
async def bulk_update_channels(
    data: ChannelBulkUpdate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> MessageResponse:
    """Bulk update multiple channels."""
    service = ChannelService(db)
    updates = [item.model_dump(exclude_unset=True) for item in data.channels]
    count = await service.bulk_update(updates)
    return MessageResponse(message=f"{count} channels updated successfully")


@router.delete("/{channel_id}", response_model=MessageResponse)
async def delete_channel(
    channel_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
    force: bool = Query(False, description="Force delete even if not orphaned"),
) -> MessageResponse:
    """Delete a channel. Use force=true to delete non-orphaned channels."""
    service = ChannelService(db)
    await service.delete(channel_id, force=force)
    return MessageResponse(message="Channel deleted successfully")


@router.patch("/{channel_id}/groups", response_model=SuccessResponse[ChannelResponse])
async def update_channel_groups(
    channel_id: int,
    data: ChannelGroupsUpdate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[ChannelResponse]:
    """Update channel's group assignments."""
    service = ChannelService(db)
    channel = await service.update_groups(channel_id, data.group_ids)
    return SuccessResponse(data=ChannelResponse.model_validate(channel))


@router.patch("/{channel_id}/packages", response_model=SuccessResponse[ChannelResponse])
async def update_channel_packages(
    channel_id: int,
    data: ChannelPackagesUpdate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[ChannelResponse]:
    """Update channel's package assignments."""
    service = ChannelService(db)
    auth_sync = AuthSyncService(db)
    current_channel = await service.get_by_id(channel_id)
    affected_package_ids = {package.id for package in current_channel.packages}
    affected_package_ids.update(data.package_ids)

    channel = await service.update_packages(channel_id, data.package_ids)
    affected_user_ids = await auth_sync.get_user_ids_for_packages(list(affected_package_ids))
    await auth_sync.sync_users_by_ids(affected_user_ids)
    return SuccessResponse(data=ChannelResponse.model_validate(channel))


@router.post("/reorder", response_model=MessageResponse)
async def reorder_channels(
    data: ReorderRequest,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> MessageResponse:
    """Reorder channels."""
    service = ChannelService(db)
    await service.reorder([{"id": item.id, "sort_order": item.sort_order} for item in data.order])
    return MessageResponse(message="Channels reordered successfully")


@router.post("/sync", response_model=SuccessResponse[SyncResultResponse])
async def sync_channels(
    _admin_id: CurrentAdminId,
    db: DBSession,
    source: StreamSource = Query(StreamSource.FLUSSONIC),
) -> SuccessResponse[SyncResultResponse]:
    """Trigger channel synchronization for a specific provider."""
    service = ChannelSyncService(db)
    result = await service.sync(source)
    return SuccessResponse(
        data=SyncResultResponse(
            source=result.source,
            total=result.total,
            new=result.new,
            updated=result.updated,
            orphaned=result.orphaned,
        )
    )


@router.get("/{channel_id}/cascade-info", response_model=SuccessResponse[ChannelCascadeInfo])
async def get_cascade_info(
    channel_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[ChannelCascadeInfo]:
    """Get cascade delete information for a channel."""
    service = ChannelService(db)
    info = await service.get_cascade_info(channel_id)
    return SuccessResponse(data=ChannelCascadeInfo(**info))
