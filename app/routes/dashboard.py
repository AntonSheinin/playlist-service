from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import func, select

from app.clients.stream_provider import get_stream_provider
from app.clients.auth_service import AuthServiceClient
from app.clients.epg_service import EpgServiceClient
from app.clients.rutv import RutvClient
from app.dependencies import CurrentAdminId, DBSession
from app.exceptions import AuthServiceError, EpgServiceError, RutvServiceError, StreamProviderError
from app.models import Channel, Group, Package, StreamSource, SyncStatus, Tariff, User, UserStatus
from app.schemas import (
    ActiveSourceCounters,
    AuthDashboardStats,
    DashboardStats,
    EpgDashboardStats,
    MessageResponse,
    RutvDashboardStats,
    StreamProviderDashboardStats,
    SuccessResponse,
)

router = APIRouter()


@router.get("/stats", response_model=SuccessResponse[DashboardStats])
async def get_stats(
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[DashboardStats]:
    """Get dashboard statistics."""
    # Channels
    stmt = select(func.count()).select_from(Channel)
    result = await db.execute(stmt)
    channels_total = result.scalar() or 0

    stmt = select(func.count()).select_from(Channel).where(Channel.sync_status == SyncStatus.SYNCED)
    result = await db.execute(stmt)
    channels_synced = result.scalar() or 0

    channels_orphaned = channels_total - channels_synced

    # Groups
    stmt = select(func.count()).select_from(Group)
    result = await db.execute(stmt)
    groups = result.scalar() or 0

    # Packages
    stmt = select(func.count()).select_from(Package)
    result = await db.execute(stmt)
    packages = result.scalar() or 0

    # Tariffs
    stmt = select(func.count()).select_from(Tariff)
    result = await db.execute(stmt)
    tariffs = result.scalar() or 0

    # Users
    stmt = select(func.count()).select_from(User)
    result = await db.execute(stmt)
    users = result.scalar() or 0

    stmt = select(func.count()).select_from(User).where(User.status == UserStatus.ENABLED)
    result = await db.execute(stmt)
    users_enabled = result.scalar() or 0

    users_disabled = users - users_enabled

    # Last sync time
    stmt = select(func.max(Channel.last_seen_at))
    result = await db.execute(stmt)
    last_sync = result.scalar()

    stats = DashboardStats(
        channels_total=channels_total,
        channels_synced=channels_synced,
        channels_orphaned=channels_orphaned,
        groups=groups,
        packages=packages,
        tariffs=tariffs,
        users=users,
        users_enabled=users_enabled,
        users_disabled=users_disabled,
        last_sync=last_sync,
    )

    return SuccessResponse(data=stats)


async def _get_provider_stats(source: StreamSource) -> StreamProviderDashboardStats:
    checked_at = datetime.now(UTC)

    try:
        client = get_stream_provider(source)
        payload = await client.get_dashboard_stats()
        stats = StreamProviderDashboardStats(
            health=payload.health,
            checked_at=checked_at,
            incoming_kbit=payload.incoming_kbit,
            outgoing_kbit=payload.outgoing_kbit,
            total_clients=payload.total_clients,
            total_sources=payload.total_sources,
            good_sources=payload.good_sources,
            broken_sources=payload.broken_sources,
            active_source_counters=(
                ActiveSourceCounters(
                    online24=payload.active_source_counters.online24,
                    restream=payload.active_source_counters.restream,
                    other=payload.active_source_counters.other,
                )
                if payload.active_source_counters is not None
                else None
            ),
            error=payload.error,
        )
    except StreamProviderError as e:
        stats = StreamProviderDashboardStats(
            health="down",
            checked_at=checked_at,
            error=str(e),
        )

    return stats


@router.get("/flussonic", response_model=SuccessResponse[StreamProviderDashboardStats])
async def get_flussonic_stats(
    _admin_id: CurrentAdminId,
) -> SuccessResponse[StreamProviderDashboardStats]:
    """Get Flussonic health and runtime stats for dashboard."""
    return SuccessResponse(data=await _get_provider_stats(StreamSource.FLUSSONIC))


@router.get("/nimble", response_model=SuccessResponse[StreamProviderDashboardStats])
async def get_nimble_stats(
    _admin_id: CurrentAdminId,
) -> SuccessResponse[StreamProviderDashboardStats]:
    """Get Nimble health and runtime stats for dashboard."""
    return SuccessResponse(data=await _get_provider_stats(StreamSource.NIMBLE))


@router.get("/auth", response_model=SuccessResponse[AuthDashboardStats])
async def get_auth_stats(_admin_id: CurrentAdminId) -> SuccessResponse[AuthDashboardStats]:
    """Get Auth service health and active token/session stats for dashboard."""
    checked_at = datetime.now(UTC)

    try:
        async with AuthServiceClient() as client:
            payload = await client.get_dashboard_stats()

        stats = AuthDashboardStats(
            health=payload["health"],
            checked_at=checked_at,
            active_tokens=payload["active_tokens"],
            active_sessions=payload["active_sessions"],
            error=payload.get("error"),
        )
    except AuthServiceError as e:
        stats = AuthDashboardStats(
            health="down",
            checked_at=checked_at,
            error=str(e),
        )

    return SuccessResponse(data=stats)


@router.get("/epg", response_model=SuccessResponse[EpgDashboardStats])
async def get_epg_stats(_admin_id: CurrentAdminId) -> SuccessResponse[EpgDashboardStats]:
    """Get EPG service health and update stats for dashboard."""
    client = EpgServiceClient()

    try:
        payload = await client.get_dashboard_stats()
        stats = EpgDashboardStats(
            health=payload["health"],
            checked_at=payload["checked_at"],
            next_fetch_at=payload["next_fetch_at"],
            last_epg_update_at=payload["last_epg_update_at"],
            sources_total=payload["sources_total"],
            last_updated_channels_count=payload["last_updated_channels_count"],
            error=payload.get("error"),
        )
    except EpgServiceError as e:
        checked_at = datetime.now(UTC)
        stats = EpgDashboardStats(
            health="down",
            checked_at=checked_at,
            error=str(e),
        )

    return SuccessResponse(data=stats)


@router.get("/rutv", response_model=SuccessResponse[RutvDashboardStats])
async def get_rutv_stats(_admin_id: CurrentAdminId) -> SuccessResponse[RutvDashboardStats]:
    """Get RUTV site health and stats for dashboard."""
    checked_at = datetime.now(UTC)
    client = RutvClient()

    try:
        payload = await client.get_dashboard_stats()
        stats = RutvDashboardStats(
            health=payload["health"],
            checked_at=checked_at,
            window_seconds=payload["window_seconds"],
            from_at=payload["from_at"],
            to_at=payload["to_at"],
            unique_visits=payload["unique_visits"],
            successful_contact_forms=payload["successful_contact_forms"],
            error=payload.get("error"),
        )
    except RutvServiceError as e:
        stats = RutvDashboardStats(
            health="down",
            checked_at=checked_at,
            error=str(e),
        )

    return SuccessResponse(data=stats)


@router.post("/epg/update", response_model=MessageResponse)
async def update_epg_now(_admin_id: CurrentAdminId) -> MessageResponse:
    """Trigger EPG service update immediately."""
    client = EpgServiceClient()
    payload = await client.trigger_fetch()

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        message = "EPG update request completed"

    return MessageResponse(message=message)
