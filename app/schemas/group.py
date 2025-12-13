from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GroupBase(BaseModel):
    """Base group fields."""

    name: str


class GroupCreate(GroupBase):
    """Group creation payload."""

    pass


class GroupUpdate(BaseModel):
    """Group update payload."""

    name: str


class GroupResponse(GroupBase):
    """Group response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sort_order: int
    created_at: datetime
    updated_at: datetime


class GroupWithCount(GroupResponse):
    """Group response with channel count."""

    channel_count: int


class GroupReorderItem(BaseModel):
    """Single item for reorder request."""

    id: int
    sort_order: int


class GroupReorderRequest(BaseModel):
    """Group reorder request."""

    order: list[GroupReorderItem]


class GroupLookup(BaseModel):
    """Group lookup item for dropdowns."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
