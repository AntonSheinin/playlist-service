from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from app.models import SyncStatus, UserStatus

T = TypeVar("T")


# Common response wrappers
class SuccessResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)
    success: bool = True
    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginatedData(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)
    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: PaginatedData[T]


class MessageResponse(BaseModel):
    success: bool = True
    message: str


# Auth
class LoginRequest(BaseModel):
    username: str
    password: str


class AdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


# Dashboard
class DashboardStats(BaseModel):
    channels_total: int
    channels_synced: int
    channels_orphaned: int
    groups: int
    packages: int
    tariffs: int
    users: int
    users_enabled: int
    users_disabled: int
    last_sync: datetime | None


# Group
class GroupCreate(BaseModel):
    name: str


class GroupUpdate(BaseModel):
    name: str


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


class GroupWithCount(GroupResponse):
    channel_count: int


class GroupReorderItem(BaseModel):
    id: int
    sort_order: int


class GroupReorderRequest(BaseModel):
    order: list[GroupReorderItem]


class GroupLookup(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# Package
class PackageCreate(BaseModel):
    name: str
    description: str | None = None


class PackageUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class PackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class PackageWithCount(PackageResponse):
    channel_count: int


class PackageDeleteInfo(BaseModel):
    tariffs: int
    users: int


class PackageLookup(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# Tariff
class TariffCreate(BaseModel):
    name: str
    description: str | None = None
    package_ids: list[int] = []


class TariffUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    package_ids: list[int] | None = None


class TariffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    packages: list[PackageLookup] = []
    created_at: datetime
    updated_at: datetime


class TariffWithCount(TariffResponse):
    package_count: int


class TariffDeleteInfo(BaseModel):
    users: int


class TariffLookup(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# Channel
class ChannelUpdate(BaseModel):
    tvg_id: str | None = None
    tvg_logo: str | None = None
    channel_number: int | None = None


class LogoUploadResponse(BaseModel):
    url: str


class ChannelBulkUpdateItem(BaseModel):
    id: int
    tvg_id: str | None = None
    tvg_logo: str | None = None
    channel_number: int | None = None
    catchup_days: int | None = None


class ChannelBulkUpdate(BaseModel):
    channels: list[ChannelBulkUpdateItem]


class ChannelGroupUpdate(BaseModel):
    group_id: int | None = None


class ChannelPackagesUpdate(BaseModel):
    package_ids: list[int]


class ChannelReorderItem(BaseModel):
    id: int
    sort_order: int


class ChannelReorderRequest(BaseModel):
    order: list[ChannelReorderItem]


class ChannelCascadeInfo(BaseModel):
    packages: int
    users: int


class SyncResultResponse(BaseModel):
    total: int
    new: int
    updated: int
    orphaned: int


class ChannelLookup(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stream_name: str
    display_name: str | None = None
    tvg_name: str | None = None


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stream_name: str
    tvg_name: str | None = None
    display_name: str | None = None
    catchup_days: int | None = None
    tvg_id: str | None = None
    tvg_logo: str | None = None
    channel_number: int | None = None
    sort_order: int = 0
    sync_status: SyncStatus = SyncStatus.SYNCED
    group_id: int | None = None
    group: GroupLookup | None = None
    packages: list[PackageLookup] = []
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# User
class UserCreate(BaseModel):
    first_name: str
    last_name: str
    agreement_number: str
    max_sessions: int = 1
    status: UserStatus = UserStatus.ENABLED
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    tariff_ids: list[int] = []
    package_ids: list[int] = []
    channel_ids: list[int] = []


class UserUpdate(BaseModel):
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


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    agreement_number: str
    max_sessions: int
    status: UserStatus
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    token: str
    auth_token_id: int | None = None
    tariffs: list[TariffLookup] = []
    packages: list[PackageLookup] = []
    channels: list[ChannelLookup] = []
    created_at: datetime
    updated_at: datetime


class UserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    agreement_number: str
    status: UserStatus
    max_sessions: int
    created_at: datetime
    tariffs: list[TariffLookup] = []


class ResolvedChannel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    stream_name: str
    display_name: str | None = None
    tvg_name: str | None = None
    group_name: str | None = None


class PlaylistPreview(BaseModel):
    filename: str
    content: str
    channel_count: int
