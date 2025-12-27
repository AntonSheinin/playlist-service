from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import ChannelNotOrphanedError, NotFoundError
from app.models import (
    Channel,
    Group,
    Package,
    SyncStatus,
    group_channels,
    package_channels,
    user_channels,
)
from app.utils.pagination import PaginatedResult, PaginationParams


class ChannelService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _group_sort_subquery(self):
        return (
            select(
                group_channels.c.channel_id.label("channel_id"),
                func.min(Group.sort_order).label("group_sort"),
            )
            .select_from(group_channels.join(Group, group_channels.c.group_id == Group.id))
            .group_by(group_channels.c.channel_id)
            .subquery()
        )

    async def get_paginated(
        self,
        pagination: PaginationParams,
        search: str | None = None,
        group_id: int | None = None,
        sync_status: SyncStatus | None = None,
        sort_by: str = "channel_number",
        sort_dir: str = "asc",
    ) -> PaginatedResult[Channel]:
        """Get paginated channels with filters."""
        stmt = select(Channel).options(
            selectinload(Channel.groups),
            selectinload(Channel.packages),
        )

        # Apply filters
        if search:
            search_filter = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Channel.stream_name.ilike(search_filter),
                    Channel.display_name.ilike(search_filter),
                    Channel.tvg_name.ilike(search_filter),
                    Channel.tvg_id.ilike(search_filter),
                )
            )

        if group_id is not None:
            stmt = stmt.where(Channel.groups.any(Group.id == group_id))

        if sync_status is not None:
            stmt = stmt.where(Channel.sync_status == sync_status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await self.db.execute(count_stmt)
        total = result.scalar() or 0

        # Apply sorting
        sort_column = getattr(Channel, sort_by, Channel.sort_order)
        if sort_by == "channel_number":
            sort_column = (
                sort_column.desc().nulls_last()
                if sort_dir == "desc"
                else sort_column.asc().nulls_last()
            )
        elif sort_dir == "desc":
            sort_column = sort_column.desc()

        # For grouped sorting: group.sort_order (nulls last), then channel.sort_order.
        if sort_by == "sort_order":
            group_sort = self._group_sort_subquery()
            stmt = stmt.outerjoin(group_sort, group_sort.c.channel_id == Channel.id).order_by(
                group_sort.c.group_sort.asc().nulls_last(),
                Channel.sort_order.asc(),
            )
        else:
            stmt = stmt.order_by(sort_column)

        # Apply pagination
        stmt = stmt.offset(pagination.offset).limit(pagination.limit)

        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return PaginatedResult(
            items=items,
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
        )

    async def get_by_id(self, channel_id: int) -> Channel:
        """Get channel by ID."""
        stmt = (
            select(Channel)
            .where(Channel.id == channel_id)
            .options(
                selectinload(Channel.groups),
                selectinload(Channel.packages),
            )
        )
        result = await self.db.execute(stmt)
        channel = result.scalar_one_or_none()

        if channel is None:
            raise NotFoundError("Channel not found")

        return channel

    async def get_by_stream_name(self, stream_name: str) -> Channel | None:
        """Get channel by stream_name."""
        stmt = select(Channel).where(Channel.stream_name == stream_name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self,
        channel_id: int,
        tvg_id: str | None = None,
        tvg_logo: str | None = None,
        channel_number: int | None = None,
    ) -> Channel:
        """Update channel (UI-managed fields only)."""
        channel = await self.get_by_id(channel_id)

        if tvg_id is not None:
            channel.tvg_id = tvg_id if tvg_id else None
        if tvg_logo is not None:
            channel.tvg_logo = tvg_logo if tvg_logo else None
        if channel_number is not None:
            channel.channel_number = channel_number if channel_number > 0 else None

        await self.db.flush()
        return await self.get_by_id(channel_id)

    async def bulk_update(
        self,
        updates: list[dict],
    ) -> int:
        """Bulk update multiple channels. Returns count of updated channels."""
        updated_count = 0
        for item in updates:
            channel_id = item.get("id")
            if not channel_id:
                continue

            stmt = select(Channel).where(Channel.id == channel_id)
            result = await self.db.execute(stmt)
            channel = result.scalar_one_or_none()

            if channel is None:
                continue

            if "tvg_id" in item:
                channel.tvg_id = item["tvg_id"] if item["tvg_id"] else None
            if "tvg_logo" in item:
                channel.tvg_logo = item["tvg_logo"] if item["tvg_logo"] else None
            if "channel_number" in item:
                val = item["channel_number"]
                channel.channel_number = val if val and val > 0 else None

            updated_count += 1

        await self.db.flush()
        return updated_count

    async def update_groups(self, channel_id: int, group_ids: list[int]) -> Channel:
        """Update channel's group assignments."""
        channel = await self.get_by_id(channel_id)

        if group_ids:
            stmt = select(Group).where(Group.id.in_(group_ids))
            result = await self.db.execute(stmt)
            groups = list(result.scalars().all())
        else:
            groups = []

        channel.groups = groups
        await self.db.flush()
        return await self.get_by_id(channel_id)

    async def update_packages(self, channel_id: int, package_ids: list[int]) -> Channel:
        """Update channel's package assignments."""
        channel = await self.get_by_id(channel_id)

        # Load packages
        stmt = select(Package).where(Package.id.in_(package_ids))
        result = await self.db.execute(stmt)
        packages = list(result.scalars().all())

        channel.packages = packages
        await self.db.flush()
        return await self.get_by_id(channel_id)

    async def delete(self, channel_id: int, force: bool = False) -> None:
        """Delete a channel. By default only orphaned channels can be deleted."""
        channel = await self.get_by_id(channel_id)

        if not force and channel.sync_status != SyncStatus.ORPHANED:
            raise ChannelNotOrphanedError()

        await self.db.delete(channel)
        await self.db.flush()

    async def reorder(self, order: list[dict[str, int]]) -> None:
        """Reorder channels. order is list of {id, sort_order}."""
        for item in order:
            stmt = select(Channel).where(Channel.id == item["id"])
            result = await self.db.execute(stmt)
            channel = result.scalar_one_or_none()
            if channel:
                channel.sort_order = item["sort_order"]
        await self.db.flush()

    async def get_cascade_info(self, channel_id: int) -> dict[str, int]:
        """Get cascade delete information for a channel."""
        # Count packages
        stmt = (
            select(func.count())
            .select_from(package_channels)
            .where(package_channels.c.channel_id == channel_id)
        )
        result = await self.db.execute(stmt)
        package_count = result.scalar() or 0

        # Count users
        stmt = (
            select(func.count())
            .select_from(user_channels)
            .where(user_channels.c.channel_id == channel_id)
        )
        result = await self.db.execute(stmt)
        user_count = result.scalar() or 0

        return {
            "packages": package_count,
            "users": user_count,
        }

    async def get_all(self) -> list[Channel]:
        """Get all channels ordered by group and sort_order."""
        group_sort = self._group_sort_subquery()
        stmt = (
            select(Channel)
            .outerjoin(group_sort, group_sort.c.channel_id == Channel.id)
            .options(selectinload(Channel.groups))
            .order_by(
                group_sort.c.group_sort.asc().nulls_last(),
                Channel.sort_order.asc(),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search(self, search: str, limit: int = 50) -> list[Channel]:
        """Search channels for dropdown."""
        search_filter = f"%{search}%"
        stmt = (
            select(Channel)
            .where(
                or_(
                    Channel.stream_name.ilike(search_filter),
                    Channel.display_name.ilike(search_filter),
                    Channel.tvg_name.ilike(search_filter),
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
