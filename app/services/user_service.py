from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError
from app.models import Channel, Package, Tariff, User, UserStatus, package_channels
from app.services.playlist_generator import PlaylistGenerator
from app.services.base import BaseService
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.token import generate_token


class UserService(BaseService[User]):
    model_class = User
    not_found_message = "User not found"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_id(self, user_id: int) -> User:
        """Get user by ID with all relationships."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.tariffs).selectinload(Tariff.packages),
                selectinload(User.packages).selectinload(Package.channels),
                selectinload(User.channels),
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise NotFoundError(self.not_found_message)

        return user

    async def get_by_playlist_name(self, playlist_name: str) -> User | None:
        """Resolve a user by playlist filename without the .m3u8 extension."""
        generator = PlaylistGenerator()
        target_filename = f"{playlist_name}.m3u8"
        target_key = target_filename.casefold()

        if "_" in playlist_name:
            agreement_candidate = playlist_name.rsplit("_", 1)[-1]
            if agreement_candidate:
                stmt = select(User).where(User.agreement_number == agreement_candidate)
                result = await self.db.execute(stmt)
                user = result.scalar_one_or_none()
                if user and generator.get_filename(user).casefold() == target_key:
                    return user

        stmt = select(User)
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        for user in users:
            if generator.get_filename(user).casefold() == target_key:
                return user

        return None

    async def get_paginated(
        self,
        pagination: PaginationParams,
        search: str | None = None,
        status: UserStatus | None = None,
        tariff_id: int | None = None,
        sort_by: str = "name",
        sort_dir: str = "asc",
    ) -> PaginatedResult[User]:
        """Get paginated users with filters."""
        stmt = select(User).options(
            selectinload(User.tariffs),
            selectinload(User.packages),
            selectinload(User.channels),
        )

        # Apply filters
        if search:
            search_filter = f"%{search}%"
            stmt = stmt.where(
                or_(
                    User.first_name.ilike(search_filter),
                    User.last_name.ilike(search_filter),
                    User.agreement_number.ilike(search_filter),
                )
            )

        if status is not None:
            stmt = stmt.where(User.status == status)

        if tariff_id is not None:
            stmt = stmt.join(User.tariffs).where(Tariff.id == tariff_id)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await self.db.execute(count_stmt)
        total = result.scalar() or 0

        # Apply sorting and pagination
        sort_map = {
            "name": (User.last_name, User.first_name),
            "agreement_number": (User.agreement_number,),
            "max_sessions": (User.max_sessions,),
            "status": (User.status,),
            "created_at": (User.created_at,),
        }
        sort_columns = sort_map.get(sort_by, sort_map["name"])
        if sort_dir == "desc":
            sort_columns = tuple(column.desc() for column in sort_columns)
        else:
            sort_columns = tuple(column.asc() for column in sort_columns)

        stmt = stmt.order_by(*sort_columns)
        stmt = stmt.offset(pagination.offset).limit(pagination.limit)

        result = await self.db.execute(stmt)
        items = list(result.scalars().unique().all())

        return PaginatedResult(
            items=items,
            total=total,
            page=pagination.page,
            per_page=pagination.per_page,
        )

    async def create(
        self,
        first_name: str,
        last_name: str,
        agreement_number: str,
        max_sessions: int = 1,
        status: UserStatus = UserStatus.ENABLED,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        tariff_ids: list[int] | None = None,
        package_ids: list[int] | None = None,
        channel_ids: list[int] | None = None,
    ) -> User:
        """Create a new user."""
        await self.check_unique(
            "agreement_number",
            agreement_number,
            message=f"Agreement number '{agreement_number}' already exists",
        )

        # Generate unique token
        token = generate_token()

        user = User(
            first_name=first_name,
            last_name=last_name,
            agreement_number=agreement_number,
            max_sessions=max_sessions,
            status=status,
            valid_from=valid_from,
            valid_until=valid_until,
            token=token,
        )

        # Load and assign tariffs
        if tariff_ids:
            stmt = select(Tariff).where(Tariff.id.in_(tariff_ids))
            result = await self.db.execute(stmt)
            user.tariffs = list(result.scalars().all())

        # Load and assign packages
        if package_ids:
            stmt = select(Package).where(Package.id.in_(package_ids))
            result = await self.db.execute(stmt)
            user.packages = list(result.scalars().all())

        # Load and assign channels
        if channel_ids:
            stmt = select(Channel).where(Channel.id.in_(channel_ids))
            result = await self.db.execute(stmt)
            user.channels = list(result.scalars().all())

        self.db.add(user)
        await self.db.flush()
        return await self.get_by_id(user.id)

    async def update(
        self,
        user_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        agreement_number: str | None = None,
        max_sessions: int | None = None,
        status: UserStatus | None = None,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        tariff_ids: list[int] | None = None,
        package_ids: list[int] | None = None,
        channel_ids: list[int] | None = None,
        clear_valid_from: bool = False,
        clear_valid_until: bool = False,
    ) -> User:
        """Update a user."""
        user = await self.get_by_id(user_id)

        if first_name is not None:
            user.first_name = first_name

        if last_name is not None:
            user.last_name = last_name

        if agreement_number is not None:
            await self.check_unique(
                "agreement_number",
                agreement_number,
                exclude_id=user_id,
                message=f"Agreement number '{agreement_number}' already exists",
            )
            user.agreement_number = agreement_number

        if max_sessions is not None:
            user.max_sessions = max_sessions

        if status is not None:
            user.status = status

        if valid_from is not None:
            user.valid_from = valid_from
        elif clear_valid_from:
            user.valid_from = None

        if valid_until is not None:
            user.valid_until = valid_until
        elif clear_valid_until:
            user.valid_until = None

        # Update tariffs
        if tariff_ids is not None:
            stmt = select(Tariff).where(Tariff.id.in_(tariff_ids))
            result = await self.db.execute(stmt)
            user.tariffs = list(result.scalars().all())

        # Update packages
        if package_ids is not None:
            stmt = select(Package).where(Package.id.in_(package_ids))
            result = await self.db.execute(stmt)
            user.packages = list(result.scalars().all())

        # Update channels
        if channel_ids is not None:
            stmt = select(Channel).where(Channel.id.in_(channel_ids))
            result = await self.db.execute(stmt)
            user.channels = list(result.scalars().all())

        await self.db.flush()
        return await self.get_by_id(user_id)

    async def delete(self, user_id: int) -> User:
        """Delete a user. Returns the user for auth service cleanup."""
        user = await self.get_by_id(user_id)
        await self.db.delete(user)
        await self.db.flush()
        return user

    async def regenerate_token(self, user_id: int) -> User:
        """Regenerate user's token."""
        user = await self.get_by_id(user_id)
        user.token = generate_token()
        await self.db.flush()
        return await self.get_by_id(user_id)

    async def resolve_channels(self, user_id: int) -> list[Channel]:
        """
        Resolve all channels for a user from:
        1. Direct channels (user_channels)
        2. Package channels (user_packages -> package_channels)
        3. Tariff channels (user_tariffs -> tariff_packages -> package_channels)

        Returns deduplicated, ordered list.
        """
        user = await self.get_by_id(user_id)

        # Collect all channel IDs from different sources
        channel_ids: set[int] = set()

        # 1. Direct channels
        for channel in user.channels:
            channel_ids.add(channel.id)

        # 2. Package channels
        for package in user.packages:
            for channel in package.channels:
                channel_ids.add(channel.id)

        # 3. Tariff channels (tariff -> packages -> channels)
        for tariff in user.tariffs:
            for package in tariff.packages:
                # Need to load channels for this package
                stmt = (
                    select(Channel.id)
                    .join(package_channels)
                    .where(package_channels.c.package_id == package.id)
                )
                result = await self.db.execute(stmt)
                for row in result:
                    channel_ids.add(row[0])

        if not channel_ids:
            return []

        # Fetch all channels ordered by channel number (fallback to sort_order for ties/nulls).
        stmt = (
            select(Channel)
            .where(Channel.id.in_(channel_ids))
            .options(selectinload(Channel.groups))
            .order_by(
                Channel.channel_number.asc().nulls_last(),
                Channel.sort_order.asc(),
                Channel.id.asc(),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def set_auth_token_id(self, user_id: int, auth_token_id: int | None) -> None:
        """Set the auth service token ID for a user."""
        user = await self.get_by_id(user_id)
        user.auth_token_id = auth_token_id
        await self.db.flush()
