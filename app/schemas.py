from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import get_settings
from app.models import StreamSource, SyncStatus, UserStatus
from app.utils.playlist_name import validate_playlist_name

T = TypeVar("T")
Health = Literal["up", "degraded", "down"]


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def validate_validity_window(
    valid_from: datetime | None,
    valid_until: datetime | None,
) -> None:
    if valid_from is not None and valid_until is not None and valid_until <= valid_from:
        raise ValueError("valid_until must be after valid_from")


# Common response wrappers
class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginatedData(BaseModel, Generic[T]):
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


# Common
class ReorderItem(BaseModel):
    id: int
    sort_order: int


class ReorderRequest(BaseModel):
    order: list[ReorderItem]


# Auth
class LoginRequest(BaseModel):
    username: str
    password: str


class AdminResponse(OrmModel):
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


class ActiveSourceCounters(BaseModel):
    online24: int
    restream: int
    other: int


class StreamProviderDashboardStats(BaseModel):
    health: Health
    checked_at: datetime
    incoming_kbit: int | None = None
    outgoing_kbit: int | None = None
    total_clients: int | None = None
    total_sources: int | None = None
    good_sources: int | None = None
    broken_sources: int | None = None
    active_source_counters: ActiveSourceCounters | None = None
    error: str | None = None


class AuthDashboardStats(BaseModel):
    health: Health
    checked_at: datetime
    active_tokens: int | None = None
    active_sessions: int | None = None
    error: str | None = None


class EpgDashboardStats(BaseModel):
    health: Health
    checked_at: datetime
    next_fetch_at: datetime | None = None
    last_epg_update_at: datetime | None = None
    sources_total: int | None = None
    last_updated_channels_count: int | None = None
    error: str | None = None


class RutvDashboardStats(BaseModel):
    health: Health
    checked_at: datetime
    window_seconds: int | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None
    unique_visits: int | None = None
    successful_contact_forms: int | None = None
    error: str | None = None


# Group
class GroupCreate(BaseModel):
    name: str


class GroupUpdate(BaseModel):
    name: str


class GroupResponse(OrmModel):
    id: int
    name: str
    sort_order: int
    created_at: datetime
    updated_at: datetime


class GroupWithCount(GroupResponse):
    channel_count: int


class GroupLookup(OrmModel):
    id: int
    name: str


# Package
class PackageCreate(BaseModel):
    name: str
    description: str | None = None


class PackageUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class PackageResponse(OrmModel):
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


class PackageLookup(OrmModel):
    id: int
    name: str


# Tariff
class TariffCreate(BaseModel):
    name: str
    description: str | None = None
    package_ids: list[int] = Field(default_factory=list)


class TariffUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    package_ids: list[int] | None = None


class TariffResponse(OrmModel):
    id: int
    name: str
    description: str | None = None
    packages: list[PackageLookup] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TariffWithCount(TariffResponse):
    package_count: int
    channel_count: int


class TariffDeleteInfo(BaseModel):
    users: int


class TariffLookup(OrmModel):
    id: int
    name: str


# Channel
class ChannelUpdate(BaseModel):
    tvg_id: str | None = None
    tvg_logo: str | None = None
    channel_number: int | None = None


class LogoUploadResponse(BaseModel):
    url: str


class LogoUrlRequest(BaseModel):
    url: str


class ChannelBulkUpdateItem(BaseModel):
    id: int
    tvg_id: str | None = None
    tvg_logo: str | None = None
    channel_number: int | None = None


class ChannelBulkUpdate(BaseModel):
    channels: list[ChannelBulkUpdateItem]


class ChannelGroupsUpdate(BaseModel):
    group_ids: list[int] = Field(default_factory=list)


class ChannelPackagesUpdate(BaseModel):
    package_ids: list[int]


class ChannelCascadeInfo(BaseModel):
    packages: int
    users: int


class SyncResultResponse(BaseModel):
    source: StreamSource
    total: int
    new: int
    updated: int
    orphaned: int


class ChannelLookup(OrmModel):
    id: int
    source: StreamSource
    stream_name: str
    display_name: str | None = None
    tvg_name: str | None = None


class PackageDetail(PackageResponse):
    channels: list[ChannelLookup] = Field(default_factory=list)


class ChannelResponse(OrmModel):
    id: int
    source: StreamSource
    stream_name: str
    tvg_name: str | None = None
    display_name: str | None = None
    catchup_days: int | None = None
    tvg_id: str | None = None
    tvg_logo: str | None = None
    channel_number: int | None = None
    sort_order: int = 0
    sync_status: SyncStatus = SyncStatus.SYNCED
    groups: list[GroupLookup] = Field(default_factory=list)
    packages: list[PackageLookup] = Field(default_factory=list)
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# User
class UserCreate(BaseModel):
    first_name: str
    last_name: str
    agreement_number: str
    max_sessions: int = Field(1, ge=1, le=100)
    status: UserStatus = UserStatus.ENABLED
    portal_allowed: bool = False
    max_portal_devices: int = Field(default=1, strict=True, ge=1, le=2_147_483_647)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    tariff_ids: list[int] = Field(default_factory=list)
    package_ids: list[int] = Field(default_factory=list)
    channel_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_validity_window(self) -> "UserCreate":
        validate_validity_window(self.valid_from, self.valid_until)
        return self


class UserUpdate(BaseModel):
    playlist_name: str | None = Field(
        default=None, json_schema_extra=lambda schema: schema.pop("default", None)
    )

    first_name: str | None = None
    last_name: str | None = None
    agreement_number: str | None = None
    max_sessions: int | None = Field(None, ge=1, le=100)
    status: UserStatus | None = None
    portal_allowed: bool | None = Field(
        default=None,
        json_schema_extra=lambda schema: schema.pop("default", None),
    )
    max_portal_devices: int | None = Field(default=None, strict=True, ge=1, le=2_147_483_647)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    clear_valid_from: bool = False
    clear_valid_until: bool = False
    tariff_ids: list[int] | None = None
    package_ids: list[int] | None = None
    channel_ids: list[int] | None = None

    @field_validator("playlist_name", mode="before", json_schema_input_type=str)
    @classmethod
    def validate_playlist_url_name(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Playlist URL name must be a string")
        return validate_playlist_name(value)

    @field_validator("portal_allowed", mode="before", json_schema_input_type=bool)
    @classmethod
    def validate_portal_allowed(cls, value: object) -> object:
        if value is None:
            raise ValueError("portal_allowed must be a boolean")
        return value

    @model_validator(mode="after")
    def validate_validity_window(self) -> "UserUpdate":
        validate_validity_window(self.valid_from, self.valid_until)
        return self


class UserSyncFields(OrmModel):
    portal_allowed: bool
    auth_synced: bool
    portal_synced: bool
    portal_sync_available: bool = False

    @model_validator(mode="after")
    def set_portal_availability(self) -> "UserSyncFields":
        self.portal_sync_available = self.portal_allowed and get_settings().active_portal_mock is not None
        if not self.portal_sync_available:
            self.portal_synced = False
        return self


class UserResponse(UserSyncFields):
    playlist_name: str
    id: int
    first_name: str
    last_name: str
    agreement_number: str
    max_sessions: int
    status: UserStatus
    max_portal_devices: int
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    token: str
    auth_token_id: int | None = None
    tariffs: list[TariffLookup] = Field(default_factory=list)
    packages: list[PackageLookup] = Field(default_factory=list)
    channels: list[ChannelLookup] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UserSaveResponse(UserResponse):
    auth_sync_result: Literal["skipped", "succeeded", "failed"]


class UserListItem(UserSyncFields):
    id: int
    first_name: str
    last_name: str
    agreement_number: str
    status: UserStatus
    max_sessions: int
    created_at: datetime
    tariffs: list[TariffLookup] = Field(default_factory=list)


class IntegrationUserSummary(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    agreement_number: str
    status: UserStatus
    portal_allowed: bool
    max_sessions: int
    valid_until: datetime | None = None


class IntegrationUserFindResponse(BaseModel):
    match_type: Literal["single", "candidates"]
    user: IntegrationUserSummary | None = None
    candidates: list[IntegrationUserSummary] = Field(default_factory=list)


class IntegrationMaxSessionsUpdate(BaseModel):
    max_sessions: int = Field(ge=1, le=100)


class IntegrationValidUntilUpdate(BaseModel):
    valid_until: datetime

    @model_validator(mode="after")
    def validate_timezone(self) -> "IntegrationValidUntilUpdate":
        if self.valid_until.tzinfo is None or self.valid_until.utcoffset() is None:
            raise ValueError("valid_until must include timezone information")
        return self


class ResolvedChannel(OrmModel):
    id: int
    source: StreamSource
    stream_name: str
    display_name: str | None = None
    tvg_name: str | None = None
    group_names: list[str] = Field(default_factory=list)


class PlaylistPreview(BaseModel):
    filename: str
    content: str
    channel_count: int


class SessionEntry(BaseModel):
    started_at: str | None = None
    ended_at: str | None = None
    duration: int | None = None
    ip: str | None = None
    channel: str | None = None
    user_agent: str | None = None


class AccessLogEntry(BaseModel):
    accessed_at: str | None = None
    ip: str | None = None
    channel: str | None = None
    action: str | None = None
    user_agent: str | None = None
