from fastapi import APIRouter, Query

from app.dependencies import CurrentAdminId, DBSession
from app.schemas import ChannelLookup, GroupLookup, PackageLookup, SuccessResponse, TariffLookup
from app.services.channel_service import ChannelService
from app.services.group_service import GroupService
from app.services.package_service import PackageService
from app.services.tariff_service import TariffService

router = APIRouter()


@router.get("/groups", response_model=SuccessResponse[list[GroupLookup]])
async def lookup_groups(
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[list[GroupLookup]]:
    """Get all groups for dropdown."""
    service = GroupService(db)
    groups = await service.get_all()
    return SuccessResponse(
        data=[GroupLookup(id=g.id, name=g.name) for g in groups]
    )


@router.get("/packages", response_model=SuccessResponse[list[PackageLookup]])
async def lookup_packages(
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[list[PackageLookup]]:
    """Get all packages for dropdown."""
    service = PackageService(db)
    packages = await service.get_all()
    return SuccessResponse(
        data=[PackageLookup(id=p.id, name=p.name) for p in packages]
    )


@router.get("/tariffs", response_model=SuccessResponse[list[TariffLookup]])
async def lookup_tariffs(
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[list[TariffLookup]]:
    """Get all tariffs for dropdown."""
    service = TariffService(db)
    tariffs = await service.get_all()
    return SuccessResponse(
        data=[TariffLookup(id=t.id, name=t.name) for t in tariffs]
    )


@router.get("/channels", response_model=SuccessResponse[list[ChannelLookup]])
async def lookup_channels(
    _admin_id: CurrentAdminId,
    db: DBSession,
    search: str = Query("", min_length=0),
    limit: int = Query(50, ge=1, le=1000),
) -> SuccessResponse[list[ChannelLookup]]:
    """Search channels for dropdown."""
    service = ChannelService(db)

    if search:
        channels = await service.search(search, limit)
    else:
        channels = await service.get_all()
        channels = channels[:limit]

    return SuccessResponse(
        data=[
            ChannelLookup(
                id=ch.id,
                stream_name=ch.stream_name,
                display_name=ch.display_name,
                tvg_name=ch.tvg_name,
            )
            for ch in channels
        ]
    )
