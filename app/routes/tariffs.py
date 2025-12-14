from fastapi import APIRouter

from app.dependencies import CurrentAdminId, DBSession
from app.schemas import (
    SuccessResponse,
    TariffCreate,
    TariffDeleteInfo,
    TariffResponse,
    TariffUpdate,
    TariffWithCount,
)
from app.services.tariff_service import TariffService

router = APIRouter()


@router.get("", response_model=SuccessResponse[list[TariffWithCount]])
async def list_tariffs(
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[list[TariffWithCount]]:
    """List all tariffs with package counts."""
    service = TariffService(db)
    tariffs = await service.get_all()

    result = []
    for tariff in tariffs:
        count = await service.get_package_count(tariff.id)
        tariff_data = TariffWithCount(
            id=tariff.id,
            name=tariff.name,
            description=tariff.description,
            packages=[{"id": p.id, "name": p.name} for p in tariff.packages],
            created_at=tariff.created_at,
            updated_at=tariff.updated_at,
            package_count=count,
        )
        result.append(tariff_data)

    return SuccessResponse(data=result)


@router.post("", response_model=SuccessResponse[TariffResponse])
async def create_tariff(
    data: TariffCreate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[TariffResponse]:
    """Create a new tariff."""
    service = TariffService(db)
    tariff = await service.create(
        name=data.name,
        description=data.description,
        package_ids=data.package_ids,
    )
    return SuccessResponse(data=TariffResponse.model_validate(tariff))


@router.patch("/{tariff_id}", response_model=SuccessResponse[TariffResponse])
async def update_tariff(
    tariff_id: int,
    data: TariffUpdate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[TariffResponse]:
    """Update a tariff."""
    service = TariffService(db)
    tariff = await service.update(
        tariff_id,
        name=data.name,
        description=data.description,
        package_ids=data.package_ids,
    )
    return SuccessResponse(data=TariffResponse.model_validate(tariff))


@router.delete("/{tariff_id}", response_model=SuccessResponse[TariffDeleteInfo])
async def delete_tariff(
    tariff_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[TariffDeleteInfo]:
    """Delete a tariff."""
    service = TariffService(db)
    info = await service.delete(tariff_id)
    return SuccessResponse(data=TariffDeleteInfo(**info))
