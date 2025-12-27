from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group, group_channels
from app.services.base import BaseService


class GroupService(BaseService[Group]):
    model_class = Group
    not_found_message = "Group not found"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

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
        await self.check_unique("name", name, message=f"Group '{name}' already exists")

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
        await self.check_unique("name", name, exclude_id=group_id, message=f"Group '{name}' already exists")

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
