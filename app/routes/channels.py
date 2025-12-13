from fastapi import APIRouter, Query

from app.dependencies import CurrentAdminId, DBSession
from app.models import SyncStatus
from app.schemas.channel import (
    ChannelCascadeInfo,
    ChannelGroupUpdate,
    ChannelPackagesUpdate,
    ChannelReorderRequest,
    ChannelResponse,
    ChannelUpdate,
    SyncResponse,
)
from app.schemas.common import MessageResponse, PaginatedData, PaginatedResponse, SuccessResponse
from app.services.channel_service import ChannelService
from app.services.channel_sync import ChannelSyncService
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
    sync_status: SyncStatus | None = None,
    sort_by: str = "sort_order",
    sort_dir: str = "asc",
) -> PaginatedResponse[ChannelResponse]:
    """List channels with pagination and filters."""
    service = ChannelService(db)
    pagination = PaginationParams(page=page, per_page=per_page)

    result = await service.get_paginated(
        pagination=pagination,
        search=search,
        group_id=group_id,
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
    """Update channel (tvg_id, tvg_logo only)."""
    service = ChannelService(db)
    channel = await service.update(
        channel_id,
        tvg_id=data.tvg_id,
        tvg_logo=data.tvg_logo,
    )
    return SuccessResponse(data=ChannelResponse.model_validate(channel))


@router.delete("/{channel_id}", response_model=MessageResponse)
async def delete_channel(
    channel_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> MessageResponse:
    """Delete an orphaned channel."""
    service = ChannelService(db)
    await service.delete(channel_id)
    return MessageResponse(message="Channel deleted successfully")


@router.patch("/{channel_id}/group", response_model=SuccessResponse[ChannelResponse])
async def update_channel_group(
    channel_id: int,
    data: ChannelGroupUpdate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[ChannelResponse]:
    """Update channel's group assignment."""
    service = ChannelService(db)
    channel = await service.update_group(channel_id, data.group_id)
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
    channel = await service.update_packages(channel_id, data.package_ids)
    return SuccessResponse(data=ChannelResponse.model_validate(channel))


@router.post("/reorder", response_model=MessageResponse)
async def reorder_channels(
    data: ChannelReorderRequest,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> MessageResponse:
    """Reorder channels."""
    service = ChannelService(db)
    await service.reorder([{"id": item.id, "sort_order": item.sort_order} for item in data.order])
    return MessageResponse(message="Channels reordered successfully")


@router.post("/sync", response_model=SuccessResponse[SyncResponse])
async def sync_channels(
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[SyncResponse]:
    """Trigger channel synchronization from Flussonic."""
    service = ChannelSyncService(db)
    result = await service.sync()
    return SuccessResponse(
        data=SyncResponse(
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
