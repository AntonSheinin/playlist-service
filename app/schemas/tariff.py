from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.package import PackageLookup


class TariffBase(BaseModel):
    """Base tariff fields."""

    name: str
    description: str | None = None


class TariffCreate(TariffBase):
    """Tariff creation payload."""

    package_ids: list[int] = []


class TariffUpdate(BaseModel):
    """Tariff update payload."""

    name: str | None = None
    description: str | None = None
    package_ids: list[int] | None = None


class TariffResponse(TariffBase):
    """Tariff response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    packages: list[PackageLookup] = []
    created_at: datetime
    updated_at: datetime


class TariffWithCount(TariffResponse):
    """Tariff response with package count."""

    package_count: int


class TariffDeleteInfo(BaseModel):
    """Tariff delete cascade information."""

    users: int


class TariffLookup(BaseModel):
    """Tariff lookup item for dropdowns."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
