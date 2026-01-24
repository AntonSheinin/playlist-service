from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.clients.auth_service import AuthServiceClient
from app.dependencies import CurrentAdminId, DBSession
from app.models import UserStatus

from app.schemas import (
    MessageResponse,
    PaginatedData,
    PaginatedResponse,
    PlaylistPreview,
    ResolvedChannel,
    SuccessResponse,
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

ACCESS_LOG_SORT_FIELDS = {"accessed_at", "ip", "channel", "action"}
SESSION_LOG_SORT_FIELDS = {"started_at", "ended_at", "duration", "ip", "channel"}


def _normalize_sort_dir(sort_dir: str) -> str:
    return "asc" if sort_dir and sort_dir.lower() == "asc" else "desc"


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    candidate = value.replace("Z", "+00:00", 1)
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _parse_sort_value(value: Any, sort_by: str, date_fields: set[str]) -> Any:
    if value is None:
        return None
    if sort_by in date_fields and isinstance(value, str):
        parsed = _parse_datetime(value)
        if parsed is None:
            return value
        return _normalize_datetime(parsed)
    return value


def _sort_items(
    items: list[dict[str, Any]],
    sort_by: str,
    sort_dir: str,
    date_fields: set[str],
) -> list[dict[str, Any]]:
    if not items:
        return items

    with_value: list[tuple[Any, dict[str, Any]]] = []
    without_value: list[dict[str, Any]] = []

    for item in items:
        value = item.get(sort_by)
        if value is None:
            without_value.append(item)
            continue
        parsed = _parse_sort_value(value, sort_by, date_fields)
        with_value.append((parsed, item))

    with_value.sort(key=lambda pair: pair[0], reverse=sort_dir == "desc")
    return [item for _, item in with_value] + without_value


def _build_access_action(result: str | None, reason: str | None) -> str:
    if not result:
        return "-"
    if reason:
        return f"{result}: {reason}"
    return result


def _map_access_log_entry(log: dict[str, Any]) -> dict[str, Any]:
    return {
        "accessed_at": log.get("timestamp"),
        "ip": log.get("client_ip"),
        "channel": log.get("stream_name"),
        "action": _build_access_action(log.get("result"), log.get("reason")),
        "user_agent": log.get("protocol"),
    }


def _map_session_log_entry(log: dict[str, Any]) -> dict[str, Any]:
    started_at = log.get("started_at")
    duration = None
    if isinstance(started_at, str):
        started_dt = _normalize_datetime(_parse_datetime(started_at))
    elif isinstance(started_at, datetime):
        started_dt = _normalize_datetime(started_at)
    else:
        started_dt = None
    if started_dt:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        duration = max(0, int((now - started_dt).total_seconds()))

    return {
        "started_at": started_at,
        "ended_at": None,
        "duration": duration,
        "ip": log.get("client_ip"),
        "channel": log.get("stream_name"),
        "user_agent": log.get("protocol"),
    }


@router.get("", response_model=PaginatedResponse[UserListItem])
async def list_users(
    _admin_id: CurrentAdminId,
    db: DBSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = None,
    status: UserStatus | None = None,
    tariff_id: int | None = None,
    sort_by: str = "name",
    sort_dir: str = "asc",
) -> PaginatedResponse[UserListItem]:
    """List users with pagination and filters."""
    service = UserService(db)
    pagination = PaginationParams(page=page, per_page=per_page)

    result = await service.get_paginated(
        pagination=pagination,
        search=search,
        status=status,
        tariff_id=tariff_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
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
            group_names=[g.name for g in sorted(ch.groups, key=lambda grp: (grp.sort_order, grp.name))],
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


@router.get("/{user_id}/sessions", response_model=SuccessResponse)
async def get_user_sessions(
    user_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000),
    sort_by: str = "started_at",
    sort_dir: str = "desc",
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
) -> SuccessResponse:
    """Get active sessions (live state) for a user from Auth Service."""
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    sort_dir = _normalize_sort_dir(sort_dir)
    if sort_by not in SESSION_LOG_SORT_FIELDS:
        sort_by = "started_at"

    auth_client = AuthServiceClient()
    sessions = await auth_client.get_user_sessions(
        user_id=user.agreement_number,
        skip=0,
        limit=1000,
    )

    from_dt = _normalize_datetime(from_date)
    to_dt = _normalize_datetime(to_date)
    filtered_sessions: list[dict[str, Any]] = []
    for session in sessions:
        started_at = session.get("started_at")
        if isinstance(started_at, str):
            started_dt = _normalize_datetime(_parse_datetime(started_at))
        elif isinstance(started_at, datetime):
            started_dt = _normalize_datetime(started_at)
        else:
            started_dt = None

        if from_dt and started_dt and started_dt < from_dt:
            continue
        if to_dt and started_dt and started_dt > to_dt:
            continue
        filtered_sessions.append(session)

    items = [_map_session_log_entry(session) for session in filtered_sessions]
    if sort_by != "started_at" or sort_dir != "desc":
        items = _sort_items(items, sort_by, sort_dir, {"started_at", "ended_at"})

    total = len(items)
    pages = 0 if total == 0 else (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    items = items[start:end]

    return SuccessResponse(
        data={
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }
    )


@router.get("/{user_id}/access-logs", response_model=SuccessResponse)
async def get_user_access_logs(
    user_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000),
    sort_by: str = "accessed_at",
    sort_dir: str = "desc",
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
) -> SuccessResponse:
    """Get access log entries (immutable audit trail) for a user from Auth Service."""
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)

    sort_dir = _normalize_sort_dir(sort_dir)
    if sort_by not in ACCESS_LOG_SORT_FIELDS:
        sort_by = "accessed_at"

    auth_client = AuthServiceClient()
    skip = (page - 1) * per_page
    logs = await auth_client.get_access_logs(
        user_id=user.agreement_number,
        start_time=from_date,
        end_time=to_date,
        skip=skip,
        limit=per_page + 1,
    )

    has_more = len(logs) > per_page
    logs = logs[:per_page]

    items = [_map_access_log_entry(log) for log in logs]
    if sort_by != "accessed_at" or sort_dir != "desc":
        items = _sort_items(items, sort_by, sort_dir, {"accessed_at"})

    total = skip + len(items) + (1 if has_more else 0)
    pages = 0 if total == 0 else (page + 1 if has_more else page)

    return SuccessResponse(
        data={
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }
    )
