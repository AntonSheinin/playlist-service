from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError
from app.models import Package, package_channels, tariff_packages, user_packages
from app.services.base import BaseService


class PackageService(BaseService[Package]):
    model_class = Package
    not_found_message = "Package not found"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_id(self, package_id: int) -> Package:
        """Get package by ID with channels."""
        stmt = (
            select(Package)
            .where(Package.id == package_id)
            .options(selectinload(Package.channels))
        )
        result = await self.db.execute(stmt)
        package = result.scalar_one_or_none()

        if package is None:
            raise NotFoundError(self.not_found_message)

        return package

    async def get_all(self) -> list[Package]:
        """Get all packages."""
        stmt = select(Package).options(selectinload(Package.channels)).order_by(Package.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_with_counts(self) -> list[tuple[Package, int]]:
        """Get all packages with channel counts in a single query."""
        stmt = (
            select(Package, func.count(package_channels.c.channel_id).label("channel_count"))
            .outerjoin(package_channels, Package.id == package_channels.c.package_id)
            .group_by(Package.id)
            .order_by(Package.name)
        )
        result = await self.db.execute(stmt)
        return [(row.Package, row.channel_count) for row in result.all()]

    async def create(self, name: str, description: str | None = None) -> Package:
        """Create a new package."""
        await self.check_unique("name", name, message=f"Package '{name}' already exists")

        package = Package(name=name, description=description)
        self.db.add(package)
        await self.db.flush()
        return await self.get_by_id(package.id)

    async def update(
        self,
        package_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> Package:
        """Update a package."""
        package = await self.get_by_id(package_id)

        if name is not None:
            await self.check_unique("name", name, exclude_id=package_id, message=f"Package '{name}' already exists")
            package.name = name

        if description is not None:
            package.description = description

        await self.db.flush()
        return await self.get_by_id(package_id)

    async def delete(self, package_id: int) -> dict[str, int]:
        """Delete a package. Returns affected counts."""
        package = await self.get_by_id(package_id)

        # Count affected tariffs
        stmt = (
            select(func.count())
            .select_from(tariff_packages)
            .where(tariff_packages.c.package_id == package_id)
        )
        result = await self.db.execute(stmt)
        tariff_count = result.scalar() or 0

        # Count affected users
        stmt = (
            select(func.count())
            .select_from(user_packages)
            .where(user_packages.c.package_id == package_id)
        )
        result = await self.db.execute(stmt)
        user_count = result.scalar() or 0

        await self.db.delete(package)
        await self.db.flush()

        return {
            "tariffs": tariff_count,
            "users": user_count,
        }
