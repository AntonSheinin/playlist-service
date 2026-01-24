import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import APIRouter, File, Query, UploadFile
from sqlalchemy import func, select

from app.dependencies import CurrentAdminId, DBSession
from app.exceptions import ValidationError
from app.models import Channel, SyncStatus
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
from app.services.channel_sync import ChannelSyncService
from app.utils.pagination import PaginationParams

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
LOGO_DIR = BASE_DIR / "media" / "logos"
MAX_LOGO_BYTES = 2 * 1024 * 1024
LOGO_URL_PREFIX = "/media/logos/"

# Magic byte signatures for image type detection
_IMAGE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
]


def _detect_image_type(data: bytes) -> str | None:
    """Detect image type from file header bytes."""
    for signature, image_type in _IMAGE_SIGNATURES:
        if data[:len(signature)] == signature:
            return image_type
    # WebP: RIFF....WEBP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def sanitize_logo_basename(value: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return base.strip("._-").lower()


def build_logo_filename(
    stream_name: str | None,
    channel_id: int | None,
    extension: str,
) -> str:
    base = sanitize_logo_basename(stream_name or "")
    if not base:
        return f"{uuid4().hex}.{extension}"

    candidate = f"{base}.{extension}"
    if not (LOGO_DIR / candidate).exists():
        return candidate

    if channel_id is not None:
        candidate = f"{base}-{channel_id}.{extension}"
        if not (LOGO_DIR / candidate).exists():
            return candidate

    counter = 2
    while True:
        candidate = f"{base}-{counter}.{extension}"
        if not (LOGO_DIR / candidate).exists():
            return candidate
        counter += 1


def resolve_logo_path(logo_url: str | None) -> Path | None:
    if not logo_url:
        return None
    path = urlparse(logo_url).path or ""
    if not path.startswith(LOGO_URL_PREFIX):
        return None
    filename = Path(path).name
    if not filename:
        return None
    return LOGO_DIR / filename


def is_safe_logo_path(path: Path) -> bool:
    try:
        return path.resolve().is_relative_to(LOGO_DIR.resolve())
    except OSError:
        return False


async def save_logo_bytes(
    content: bytes,
    stream_name: str | None = None,
    channel_id: int | None = None,
) -> str:
    if not content:
        raise ValidationError("Uploaded file is empty")
    if len(content) > MAX_LOGO_BYTES:
        raise ValidationError("Logo exceeds 2MB limit")

    image_type = _detect_image_type(content)
    if image_type is None:
        raise ValidationError("Unsupported image type")

    extension = "jpg" if image_type == "jpeg" else image_type
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    filename = build_logo_filename(stream_name, channel_id, extension)
    logo_path = LOGO_DIR / filename
    logo_path.write_bytes(content)

    return f"{LOGO_URL_PREFIX}{filename}"


async def save_logo_file(
    upload: UploadFile,
    stream_name: str | None = None,
    channel_id: int | None = None,
) -> str:
    if upload.content_type and not upload.content_type.startswith("image/"):
        raise ValidationError("Only image uploads are allowed")

    content = await upload.read(MAX_LOGO_BYTES + 1)
    await upload.close()

    return await save_logo_bytes(content, stream_name=stream_name, channel_id=channel_id)


async def save_logo_url(
    url: str,
    stream_name: str | None = None,
    channel_id: int | None = None,
) -> str:
    if not url:
        raise ValidationError("Logo URL is required")

    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async with client.stream("GET", url) as response:
            if response.status_code >= 400:
                raise ValidationError("Failed to download logo")

            content_type = response.headers.get("Content-Type", "")
            if content_type and not content_type.startswith("image/"):
                raise ValidationError("Logo URL must point to an image")

            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > MAX_LOGO_BYTES:
                    raise ValidationError("Logo exceeds 2MB limit")

    return await save_logo_bytes(bytes(data), stream_name=stream_name, channel_id=channel_id)


@router.get("", response_model=PaginatedResponse[ChannelResponse])
async def list_channels(
    _admin_id: CurrentAdminId,
    db: DBSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = None,
    group_id: int | None = None,
    sync_status: SyncStatus | None = None,
    sort_by: str = "channel_number",
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
    channel = await service.update_packages(channel_id, data.package_ids)
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
) -> SuccessResponse[SyncResultResponse]:
    """Trigger channel synchronization from Flussonic."""
    service = ChannelSyncService(db)
    result = await service.sync()
    return SuccessResponse(
        data=SyncResultResponse(
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
