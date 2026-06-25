from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateEntryError, NotFoundError
from app.models import Group, group_channels


class GroupService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, group_id: int) -> Group:
        stmt = select(Group).where(Group.id == group_id)
        result = await self.db.execute(stmt)
        group = result.scalar_one_or_none()
        if group is None:
            raise NotFoundError("Group not found")
        return group

    async def _ensure_name_available(
        self,
        name: str,
        *,
        exclude_id: int | None = None,
    ) -> None:
        stmt = select(Group.id).where(Group.name == name)
        if exclude_id is not None:
            stmt = stmt.where(Group.id != exclude_id)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateEntryError(f"Group '{name}' already exists")

    async def get_all(self) -> list[Group]:
        """Get all groups ordered by sort_order."""
        stmt = select(Group).order_by(Group.sort_order, Group.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_with_counts(self) -> list[tuple[Group, int]]:
        """Get all groups with channel counts in a single query."""
        stmt = (
            select(Group, func.count(group_channels.c.channel_id).label("channel_count"))
            .outerjoin(group_channels, group_channels.c.group_id == Group.id)
            .group_by(Group.id)
            .order_by(Group.sort_order, Group.name)
        )
        result = await self.db.execute(stmt)
        return [(row.Group, row.channel_count) for row in result.all()]

    async def create(self, name: str) -> Group:
        """Create a new group."""
        await self._ensure_name_available(name)

        # Get max sort_order for new group
        stmt = select(func.coalesce(func.max(Group.sort_order), 0))
        result = await self.db.execute(stmt)
        max_order = result.scalar() or 0

        group = Group(name=name, sort_order=max_order + 1)
        self.db.add(group)
        await self.db.flush()
        return await self.get_by_id(group.id)

    async def update(self, group_id: int, name: str) -> Group:
        """Update a group."""
        group = await self.get_by_id(group_id)
        await self._ensure_name_available(name, exclude_id=group_id)

        group.name = name
        await self.db.flush()
        return await self.get_by_id(group_id)

    async def delete(self, group_id: int) -> int:
        """Delete a group. Returns count of affected channels."""
        group = await self.get_by_id(group_id)

        # Count affected channels
        stmt = select(func.count()).select_from(group_channels).where(group_channels.c.group_id == group_id)
        result = await self.db.execute(stmt)
        affected_count = result.scalar() or 0

        await self.db.delete(group)
        await self.db.flush()
        return affected_count

    async def reorder(self, order: list[dict[str, int]]) -> None:
        """Reorder groups, preserving current behavior of ignoring missing IDs."""
        for item in order:
            stmt = select(Group).where(Group.id == item["id"])
            result = await self.db.execute(stmt)
            group = result.scalar_one_or_none()
            if group:
                group.sort_order = item["sort_order"]
        await self.db.flush()
