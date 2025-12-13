from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import UserStatus
from app.schemas.channel import ChannelLookup
from app.schemas.package import PackageLookup
from app.schemas.tariff import TariffLookup


class UserBase(BaseModel):
    """Base user fields."""

    first_name: str
    last_name: str
    agreement_number: str
    max_sessions: int = 1
    status: UserStatus = UserStatus.ENABLED
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class UserCreate(UserBase):
    """User creation payload."""

    tariff_ids: list[int] = []
    package_ids: list[int] = []
    channel_ids: list[int] = []


class UserUpdate(BaseModel):
    """User update payload."""

    first_name: str | None = None
    last_name: str | None = None
    agreement_number: str | None = None
    max_sessions: int | None = None
    status: UserStatus | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    clear_valid_from: bool = False
    clear_valid_until: bool = False
    tariff_ids: list[int] | None = None
    package_ids: list[int] | None = None
    channel_ids: list[int] | None = None


class UserBrief(BaseModel):
    """Brief user info for lists."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    agreement_number: str
    status: UserStatus
    max_sessions: int
    created_at: datetime


class UserResponse(UserBase):
    """User response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    token: str
    auth_token_id: int | None = None
    tariffs: list[TariffLookup] = []
    packages: list[PackageLookup] = []
    channels: list[ChannelLookup] = []
    created_at: datetime
    updated_at: datetime


class UserListItem(UserBrief):
    """User item for list view."""

    tariffs: list[TariffLookup] = []


class ResolvedChannel(BaseModel):
    """Channel in resolved list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stream_name: str
    display_name: str | None = None
    tvg_name: str | None = None
    group_name: str | None = None


class PlaylistPreview(BaseModel):
    """Playlist preview content."""

    filename: str
    content: str
    channel_count: int
