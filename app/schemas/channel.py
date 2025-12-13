from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import SyncStatus
from app.schemas.group import GroupLookup


class PackageBrief(BaseModel):
    """Brief package info for channel response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ChannelBase(BaseModel):
    """Base channel fields."""

    stream_name: str
    tvg_name: str | None = None
    display_name: str | None = None
    stream_base_url: str
    catchup_days: int | None = None
    tvg_id: str | None = None
    tvg_logo: str | None = None
    sort_order: int = 0
    sync_status: SyncStatus = SyncStatus.SYNCED


class ChannelResponse(ChannelBase):
    """Channel response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int | None = None
    group: GroupLookup | None = None
    packages: list[PackageBrief] = []
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ChannelUpdate(BaseModel):
    """Channel update payload (UI-managed fields only)."""

    tvg_id: str | None = None
    tvg_logo: str | None = None


class ChannelGroupUpdate(BaseModel):
    """Channel group assignment update."""

    group_id: int | None = None


class ChannelPackagesUpdate(BaseModel):
    """Channel packages assignment update."""

    package_ids: list[int]


class ChannelReorderItem(BaseModel):
    """Single item for reorder request."""

    id: int
    sort_order: int


class ChannelReorderRequest(BaseModel):
    """Channel reorder request."""

    order: list[ChannelReorderItem]


class ChannelCascadeInfo(BaseModel):
    """Cascade delete information for a channel."""

    packages: int
    users: int


class SyncResponse(BaseModel):
    """Channel sync response."""

    total: int
    new: int
    updated: int
    orphaned: int


class ChannelLookup(BaseModel):
    """Channel lookup item for dropdowns."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stream_name: str
    display_name: str | None = None
    tvg_name: str | None = None
