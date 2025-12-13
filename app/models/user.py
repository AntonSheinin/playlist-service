import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.channel import Channel
    from app.models.package import Package
    from app.models.tariff import Tariff


class UserStatus(str, enum.Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


user_tariffs = Table(
    "user_tariffs",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("tariff_id", Integer, ForeignKey("tariffs.id", ondelete="CASCADE"), primary_key=True),
)

user_packages = Table(
    "user_packages",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("package_id", Integer, ForeignKey("packages.id", ondelete="CASCADE"), primary_key=True),
)

user_channels = Table(
    "user_channels",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("channel_id", Integer, ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    agreement_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, native_enum=False),
        default=UserStatus.ENABLED,
        index=True,
    )
    max_sessions: Mapped[int] = mapped_column(default=1, nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    auth_token_id: Mapped[int | None] = mapped_column(nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    tariffs: Mapped[list["Tariff"]] = relationship(
        "Tariff",
        secondary=user_tariffs,
        lazy="selectin",
    )
    packages: Mapped[list["Package"]] = relationship(
        "Package",
        secondary=user_packages,
        lazy="selectin",
    )
    channels: Mapped[list["Channel"]] = relationship(
        "Channel",
        secondary=user_channels,
        lazy="selectin",
    )
