from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.channel import package_channels

if TYPE_CHECKING:
    from app.models.channel import Channel
    from app.models.tariff import Tariff


class Package(Base, TimestampMixin):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    channels: Mapped[list["Channel"]] = relationship(
        "Channel",
        secondary=package_channels,
        back_populates="packages",
        lazy="selectin",
    )
    tariffs: Mapped[list["Tariff"]] = relationship(
        "Tariff",
        secondary="tariff_packages",
        back_populates="packages",
        lazy="selectin",
    )
