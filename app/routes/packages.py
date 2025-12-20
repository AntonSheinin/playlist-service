from fastapi import APIRouter

from app.dependencies import CurrentAdminId, DBSession
from app.schemas import (
    PackageCreate,
    PackageDeleteInfo,
    PackageResponse,
    PackageUpdate,
    PackageWithCount,
    SuccessResponse,
)
from app.services.package_service import PackageService

router = APIRouter()


@router.get("", response_model=SuccessResponse[list[PackageWithCount]])
async def list_packages(
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[list[PackageWithCount]]:
    """List all packages with channel counts."""
    service = PackageService(db)
    packages_with_counts = await service.get_all_with_counts()

    result = [
        PackageWithCount(
            id=package.id,
            name=package.name,
            description=package.description,
            created_at=package.created_at,
            updated_at=package.updated_at,
            channel_count=count,
        )
        for package, count in packages_with_counts
    ]

    return SuccessResponse(data=result)


@router.post("", response_model=SuccessResponse[PackageResponse])
async def create_package(
    data: PackageCreate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[PackageResponse]:
    """Create a new package."""
    service = PackageService(db)
    package = await service.create(data.name, data.description)
    return SuccessResponse(data=PackageResponse.model_validate(package))


@router.patch("/{package_id}", response_model=SuccessResponse[PackageResponse])
async def update_package(
    package_id: int,
    data: PackageUpdate,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[PackageResponse]:
    """Update a package."""
    service = PackageService(db)
    package = await service.update(
        package_id,
        name=data.name,
        description=data.description,
    )
    return SuccessResponse(data=PackageResponse.model_validate(package))


@router.delete("/{package_id}", response_model=SuccessResponse[PackageDeleteInfo])
async def delete_package(
    package_id: int,
    _admin_id: CurrentAdminId,
    db: DBSession,
) -> SuccessResponse[PackageDeleteInfo]:
    """Delete a package."""
    service = PackageService(db)
    info = await service.delete(package_id)
    return SuccessResponse(data=PackageDeleteInfo(**info))
