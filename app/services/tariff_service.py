from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import DuplicateEntryError, NotFoundError
from app.models import Package, Tariff, user_tariffs


class TariffService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all(self) -> list[Tariff]:
        """Get all tariffs."""
        stmt = select(Tariff).options(selectinload(Tariff.packages)).order_by(Tariff.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, tariff_id: int) -> Tariff:
        """Get tariff by ID."""
        stmt = (
            select(Tariff)
            .where(Tariff.id == tariff_id)
            .options(selectinload(Tariff.packages))
        )
        result = await self.db.execute(stmt)
        tariff = result.scalar_one_or_none()

        if tariff is None:
            raise NotFoundError("Tariff not found")

        return tariff

    async def create(
        self,
        name: str,
        description: str | None = None,
        package_ids: list[int] | None = None,
    ) -> Tariff:
        """Create a new tariff."""
        # Check for duplicate name
        stmt = select(Tariff).where(Tariff.name == name)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateEntryError(f"Tariff '{name}' already exists")

        tariff = Tariff(name=name, description=description)

        # Load and assign packages
        if package_ids:
            stmt = select(Package).where(Package.id.in_(package_ids))
            result = await self.db.execute(stmt)
            packages = list(result.scalars().all())
            tariff.packages = packages

        self.db.add(tariff)
        await self.db.flush()
        return await self.get_by_id(tariff.id)

    async def update(
        self,
        tariff_id: int,
        name: str | None = None,
        description: str | None = None,
        package_ids: list[int] | None = None,
    ) -> Tariff:
        """Update a tariff."""
        tariff = await self.get_by_id(tariff_id)

        if name is not None:
            # Check for duplicate name (excluding current tariff)
            stmt = select(Tariff).where(Tariff.name == name, Tariff.id != tariff_id)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is not None:
                raise DuplicateEntryError(f"Tariff '{name}' already exists")
            tariff.name = name

        if description is not None:
            tariff.description = description

        if package_ids is not None:
            # Load and assign packages
            stmt = select(Package).where(Package.id.in_(package_ids))
            result = await self.db.execute(stmt)
            packages = list(result.scalars().all())
            tariff.packages = packages

        await self.db.flush()
        return await self.get_by_id(tariff_id)

    async def delete(self, tariff_id: int) -> dict[str, int]:
        """Delete a tariff. Returns affected user count."""
        tariff = await self.get_by_id(tariff_id)

        # Count affected users
        stmt = (
            select(func.count())
            .select_from(user_tariffs)
            .where(user_tariffs.c.tariff_id == tariff_id)
        )
        result = await self.db.execute(stmt)
        user_count = result.scalar() or 0

        await self.db.delete(tariff)
        await self.db.flush()

        return {"users": user_count}

    async def get_package_count(self, tariff_id: int) -> int:
        """Get count of packages in a tariff."""
        tariff = await self.get_by_id(tariff_id)
        return len(tariff.packages)
