from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PackageBase(BaseModel):
    """Base package fields."""

    name: str
    description: str | None = None


class PackageCreate(PackageBase):
    """Package creation payload."""

    pass


class PackageUpdate(BaseModel):
    """Package update payload."""

    name: str | None = None
    description: str | None = None


class PackageResponse(PackageBase):
    """Package response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PackageWithCount(PackageResponse):
    """Package response with channel count."""

    channel_count: int


class PackageDeleteInfo(BaseModel):
    """Package delete cascade information."""

    tariffs: int
    users: int


class PackageLookup(BaseModel):
    """Package lookup item for dropdowns."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
