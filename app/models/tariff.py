from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.package import Package


tariff_packages = Table(
    "tariff_packages",
    Base.metadata,
    Column("tariff_id", Integer, ForeignKey("tariffs.id", ondelete="CASCADE"), primary_key=True),
    Column("package_id", Integer, ForeignKey("packages.id", ondelete="CASCADE"), primary_key=True),
)


class Tariff(Base, TimestampMixin):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    packages: Mapped[list["Package"]] = relationship(
        "Package",
        secondary=tariff_packages,
        back_populates="tariffs",
        lazy="selectin",
    )
