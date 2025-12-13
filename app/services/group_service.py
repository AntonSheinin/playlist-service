from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateEntryError, NotFoundError
from app.models import Channel, Group


class GroupService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all(self) -> list[Group]:
        """Get all groups ordered by sort_order."""
        stmt = select(Group).order_by(Group.sort_order, Group.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, group_id: int) -> Group:
        """Get group by ID."""
        stmt = select(Group).where(Group.id == group_id)
        result = await self.db.execute(stmt)
        group = result.scalar_one_or_none()

        if group is None:
            raise NotFoundError("Group not found")

        return group

    async def create(self, name: str) -> Group:
        """Create a new group."""
        # Check for duplicate name
        stmt = select(Group).where(Group.name == name)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateEntryError(f"Group '{name}' already exists")

        # Get max sort_order for new group
        stmt = select(func.coalesce(func.max(Group.sort_order), 0))
        result = await self.db.execute(stmt)
        max_order = result.scalar() or 0

        group = Group(name=name, sort_order=max_order + 1)
        self.db.add(group)
        await self.db.flush()
        return group

    async def update(self, group_id: int, name: str) -> Group:
        """Update a group."""
        group = await self.get_by_id(group_id)

        # Check for duplicate name (excluding current group)
        stmt = select(Group).where(Group.name == name, Group.id != group_id)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateEntryError(f"Group '{name}' already exists")

        group.name = name
        await self.db.flush()
        return group

    async def delete(self, group_id: int) -> int:
        """Delete a group. Returns count of affected channels."""
        group = await self.get_by_id(group_id)

        # Count affected channels
        stmt = select(func.count()).select_from(Channel).where(Channel.group_id == group_id)
        result = await self.db.execute(stmt)
        affected_count = result.scalar() or 0

        await self.db.delete(group)
        await self.db.flush()
        return affected_count

    async def reorder(self, order: list[dict[str, int]]) -> None:
        """Reorder groups. order is list of {id, sort_order}."""
        for item in order:
            stmt = select(Group).where(Group.id == item["id"])
            result = await self.db.execute(stmt)
            group = result.scalar_one_or_none()
            if group:
                group.sort_order = item["sort_order"]
        await self.db.flush()

    async def get_channel_count(self, group_id: int) -> int:
        """Get count of channels in a group."""
        stmt = select(func.count()).select_from(Channel).where(Channel.group_id == group_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
