from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import ChannelNotOrphanedError, NotFoundError
from app.models import Channel, Group, Package, SyncStatus, package_channels, user_channels
from app.utils.pagination import PaginatedResult, PaginationParams


class ChannelService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_paginated(
        self,
        pagination: PaginationParams,
        search: str | None = None,
        group_id: int | None = None,
        sync_status: SyncStatus | None = None,
        sort_by: str = "sort_order",
        sort_dir: str = "asc",
    ) -> PaginatedResult[Channel]:
        """Get paginated channels with filters."""
        stmt = select(Channel).options(
            selectinload(Channel.group),
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
            stmt = stmt.where(Channel.group_id == group_id)

        if sync_status is not None:
            stmt = stmt.where(Channel.sync_status == sync_status)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await self.db.execute(count_stmt)
        total = result.scalar() or 0

        # Apply sorting
        sort_column = getattr(Channel, sort_by, Channel.sort_order)
        if sort_dir == "desc":
            sort_column = sort_column.desc()

        # For proper playlist ordering: group.sort_order (nulls last), then channel.sort_order
        if sort_by == "sort_order":
            stmt = stmt.outerjoin(Group).order_by(
                Group.sort_order.asc().nulls_last(),
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
                selectinload(Channel.group),
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
    ) -> Channel:
        """Update channel (UI-managed fields only)."""
        channel = await self.get_by_id(channel_id)

        if tvg_id is not None:
            channel.tvg_id = tvg_id if tvg_id else None
        if tvg_logo is not None:
            channel.tvg_logo = tvg_logo if tvg_logo else None

        await self.db.flush()
        return channel

    async def update_group(self, channel_id: int, group_id: int | None) -> Channel:
        """Update channel's group assignment."""
        channel = await self.get_by_id(channel_id)
        channel.group_id = group_id
        await self.db.flush()
        return channel

    async def update_packages(self, channel_id: int, package_ids: list[int]) -> Channel:
        """Update channel's package assignments."""
        channel = await self.get_by_id(channel_id)

        # Load packages
        stmt = select(Package).where(Package.id.in_(package_ids))
        result = await self.db.execute(stmt)
        packages = list(result.scalars().all())

        channel.packages = packages
        await self.db.flush()
        return channel

    async def delete(self, channel_id: int) -> None:
        """Delete an orphaned channel."""
        channel = await self.get_by_id(channel_id)

        if channel.sync_status != SyncStatus.ORPHANED:
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
        stmt = (
            select(Channel)
            .outerjoin(Group)
            .options(selectinload(Channel.group))
            .order_by(
                Group.sort_order.asc().nulls_last(),
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
