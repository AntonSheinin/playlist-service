from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import DuplicateEntryError, NotFoundError
from app.models import Package, tariff_packages, user_packages


class PackageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all(self) -> list[Package]:
        """Get all packages."""
        stmt = select(Package).options(selectinload(Package.channels)).order_by(Package.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, package_id: int) -> Package:
        """Get package by ID."""
        stmt = (
            select(Package)
            .where(Package.id == package_id)
            .options(selectinload(Package.channels))
        )
        result = await self.db.execute(stmt)
        package = result.scalar_one_or_none()

        if package is None:
            raise NotFoundError("Package not found")

        return package

    async def create(self, name: str, description: str | None = None) -> Package:
        """Create a new package."""
        # Check for duplicate name
        stmt = select(Package).where(Package.name == name)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateEntryError(f"Package '{name}' already exists")

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
            # Check for duplicate name (excluding current package)
            stmt = select(Package).where(Package.name == name, Package.id != package_id)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is not None:
                raise DuplicateEntryError(f"Package '{name}' already exists")
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

    async def get_channel_count(self, package_id: int) -> int:
        """Get count of channels in a package."""
        package = await self.get_by_id(package_id)
        return len(package.channels)
