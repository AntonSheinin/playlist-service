from fastapi import APIRouter
from sqlalchemy import func, select

from app.dependencies import CurrentAdminId, DBSession
from app.models import Channel, Group, Package, SyncStatus, Tariff, User, UserStatus
from app.schemas.common import SuccessResponse
from app.schemas.dashboard import DashboardStats

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
