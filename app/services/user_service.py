from datetime import UTC, datetime

from sqlalchemy import func, or_, select, union
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import CompoundSelect

from app.exceptions import DuplicateEntryError, NotFoundError, ValidationError
from app.models import (
    Channel,
    Package,
    Tariff,
    User,
    UserStatus,
    package_channels,
    tariff_packages,
    user_channels,
    user_packages,
    user_tariffs,
)
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.playlist_name import generate_playlist_name, validate_playlist_name
from app.utils.token import generate_token


def _to_db_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def user_channel_assignments(user_ids: list[int] | None = None) -> CompoundSelect:
    """Select direct and inherited (user_id, channel_id) pairs."""
    direct = select(user_channels.c.user_id, user_channels.c.channel_id)
    packages = select(user_packages.c.user_id, package_channels.c.channel_id).select_from(
        user_packages.join(package_channels, user_packages.c.package_id == package_channels.c.package_id)
    )
    tariffs = select(user_tariffs.c.user_id, package_channels.c.channel_id).select_from(
        user_tariffs.join(tariff_packages, user_tariffs.c.tariff_id == tariff_packages.c.tariff_id)
        .join(package_channels, tariff_packages.c.package_id == package_channels.c.package_id)
    )
    if user_ids is not None:
        direct = direct.where(user_channels.c.user_id.in_(user_ids))
        packages = packages.where(user_packages.c.user_id.in_(user_ids))
        tariffs = tariffs.where(user_tariffs.c.user_id.in_(user_ids))
    return union(direct, packages, tariffs)


class UserService:
    not_found_message = "User not found"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _ensure_agreement_available(
        self,
        agreement_number: str,
        *,
        exclude_id: int | None = None,
    ) -> None:
        stmt = select(User.id).where(User.agreement_number == agreement_number)
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateEntryError(f"Agreement number '{agreement_number}' already exists")

    async def _ensure_playlist_name_available(
        self, playlist_name: str, *, exclude_id: int | None = None
    ) -> None:
        stmt = select(User.id).where(func.lower(User.playlist_name) == func.lower(playlist_name))
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateEntryError("Playlist URL name is already in use")

    async def _flush_user(self) -> None:
        try:
            await self.db.flush()
        except IntegrityError as error:
            cause = error.orig.__cause__
            if (
                getattr(cause, "constraint_name", None) == "uq_users_playlist_name_lower"
                or "index 'uq_users_playlist_name_lower'" in str(error.orig)
            ):
                raise DuplicateEntryError("Playlist URL name is already in use") from error
            raise

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

    async def find_exact_for_integration(self, query: str) -> list[User]:
        """Find users by exact agreement, first name, last name, or full name."""
        normalized_query = query.strip().casefold()
        if not normalized_query:
            return []

        normalized_full_name = func.lower(
            func.trim(User.first_name + " " + User.last_name)
        )
        normalized_reversed_full_name = func.lower(
            func.trim(User.last_name + " " + User.first_name)
        )
        stmt = (
            select(User)
            .where(
                or_(
                    func.lower(func.trim(User.agreement_number)) == normalized_query,
                    func.lower(func.trim(User.first_name)) == normalized_query,
                    func.lower(func.trim(User.last_name)) == normalized_query,
                    normalized_full_name == normalized_query,
                    normalized_reversed_full_name == normalized_query,
                )
            )
            .order_by(User.id.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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
            search_conditions = [
                User.first_name.ilike(search_filter),
                User.last_name.ilike(search_filter),
                User.agreement_number.ilike(search_filter),
            ]
            if search.isdigit():
                search_conditions.append(User.id == int(search))
            stmt = stmt.where(or_(*search_conditions))

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
            "portal_allowed": (User.portal_allowed,),
            "created_at": (User.created_at,),
        }
        sort_columns = sort_map.get(sort_by, sort_map["name"])
        if sort_dir == "desc":
            sort_columns = tuple(column.desc() for column in sort_columns)
        else:
            sort_columns = tuple(column.asc() for column in sort_columns)

        if sort_by == "portal_allowed":
            sort_columns = (*sort_columns, User.id.asc())

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
        portal_allowed: bool = False,
        max_portal_devices: int = 1,
    ) -> User:
        """Create a new user."""
        if not portal_allowed and max_portal_devices != 1:
            raise ValidationError("Allow portal access before changing the portal device limit")
        await self._ensure_agreement_available(agreement_number)

        try:
            playlist_name = generate_playlist_name(first_name, last_name, agreement_number)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        await self._ensure_playlist_name_available(playlist_name)

        # Generate unique token
        token = generate_token()

        user = User(
            first_name=first_name,
            last_name=last_name,
            agreement_number=agreement_number,
            playlist_name=playlist_name,
            max_sessions=max_sessions,
            status=status,
            portal_allowed=portal_allowed,
            max_portal_devices=max_portal_devices,
            valid_from=_to_db_datetime(valid_from) if valid_from is not None else None,
            valid_until=_to_db_datetime(valid_until) if valid_until is not None else None,
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
        await self._flush_user()
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
        portal_allowed: bool | None = None,
        playlist_name: str | None = None,
        max_portal_devices: int | None = None,
    ) -> User:
        """Update a user."""
        user = await self.get_by_id(user_id)
        next_portal_allowed = user.portal_allowed if portal_allowed is None else portal_allowed
        device_limit_changed = max_portal_devices is not None and max_portal_devices != user.max_portal_devices
        if device_limit_changed and not next_portal_allowed:
            raise ValidationError("Allow portal access before changing the portal device limit")

        if playlist_name is not None and playlist_name != user.playlist_name:
            try:
                validate_playlist_name(playlist_name)
            except ValueError as error:
                raise ValidationError(str(error)) from error
            await self._ensure_playlist_name_available(playlist_name, exclude_id=user_id)
            user.playlist_name = playlist_name
            # Enforce uniqueness before further queries can autoflush this change.
            await self._flush_user()

        if first_name is not None:
            user.first_name = first_name

        if last_name is not None:
            user.last_name = last_name

        if agreement_number is not None:
            await self._ensure_agreement_available(agreement_number, exclude_id=user_id)
            user.agreement_number = agreement_number

        if max_sessions is not None:
            user.max_sessions = max_sessions

        if status is not None:
            user.status = status

        if user.portal_allowed != next_portal_allowed or device_limit_changed:
            user.portal_synced = False
        user.portal_allowed = next_portal_allowed
        if max_portal_devices is not None:
            user.max_portal_devices = max_portal_devices

        if valid_from is not None:
            user.valid_from = _to_db_datetime(valid_from)
        elif clear_valid_from:
            user.valid_from = None

        if valid_until is not None:
            user.valid_until = _to_db_datetime(valid_until)
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

        await self._flush_user()
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
        user.auth_previous_token = user.token
        user.token = generate_token()
        user.auth_synced = False
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
        result = await self.db.execute(select(User.id).where(User.id == user_id))
        if result.scalar_one_or_none() is None:
            raise NotFoundError(self.not_found_message)

        assignments = user_channel_assignments([user_id]).subquery()
        # Fetch all channels ordered by channel number (fallback to sort_order for ties/nulls).
        stmt = (
            select(Channel)
            .join(assignments, assignments.c.channel_id == Channel.id)
            .options(selectinload(Channel.groups))
            .order_by(
                Channel.channel_number.asc().nulls_last(),
                Channel.sort_order.asc(),
                Channel.id.asc(),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
