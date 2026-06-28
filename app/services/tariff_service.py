from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import DuplicateEntryError, NotFoundError
from app.models import Package, Tariff, tariff_packages, user_tariffs


class TariffService:
    not_found_message = "Tariff not found"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _ensure_name_available(
        self,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> None:
        stmt = select(Tariff.id).where(Tariff.name == name)
        if exclude_id is not None:
            stmt = stmt.where(Tariff.id != exclude_id)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateEntryError(f"Tariff '{name}' already exists")

    async def get_by_id(self, tariff_id: int) -> Tariff:
        """Get tariff by ID with packages."""
        stmt = (
            select(Tariff)
            .where(Tariff.id == tariff_id)
            .options(selectinload(Tariff.packages))
        )
        result = await self.db.execute(stmt)
        tariff = result.scalar_one_or_none()

        if tariff is None:
            raise NotFoundError(self.not_found_message)

        return tariff

    async def get_all(self) -> list[Tariff]:
        """Get all tariffs."""
        stmt = select(Tariff).options(selectinload(Tariff.packages)).order_by(Tariff.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_with_counts(self) -> list[tuple[Tariff, int]]:
        """Get all tariffs with package counts in a single query."""
        stmt = (
            select(Tariff, func.count(tariff_packages.c.package_id).label("package_count"))
            .outerjoin(tariff_packages, Tariff.id == tariff_packages.c.tariff_id)
            .group_by(Tariff.id)
            .order_by(Tariff.name)
            .options(selectinload(Tariff.packages))
        )
        result = await self.db.execute(stmt)
        return [(row.Tariff, row.package_count) for row in result.all()]

    async def create(
        self,
        name: str,
        description: str | None = None,
        package_ids: list[int] | None = None,
    ) -> Tariff:
        """Create a new tariff."""
        await self._ensure_name_available(name)

        tariff = Tariff(name=name, description=description)

        if package_ids:
            stmt = select(Package).where(Package.id.in_(package_ids))
            result = await self.db.execute(stmt)
            tariff.packages = list(result.scalars().all())

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
            await self._ensure_name_available(name, exclude_id=tariff_id)
            tariff.name = name

        if description is not None:
            tariff.description = description

        if package_ids is not None:
            stmt = select(Package).where(Package.id.in_(package_ids))
            result = await self.db.execute(stmt)
            tariff.packages = list(result.scalars().all())

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
