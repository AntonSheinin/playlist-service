import enum
from datetime import datetime

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now(), onupdate=func.now())


class SyncStatus(str, enum.Enum):
    SYNCED = "synced"
    ORPHANED = "orphaned"


class UserStatus(str, enum.Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


# Association tables
package_channels = Table(
    "package_channels",
    Base.metadata,
    Column("package_id", Integer, ForeignKey("packages.id", ondelete="CASCADE"), primary_key=True),
    Column("channel_id", Integer, ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True),
)

tariff_packages = Table(
    "tariff_packages",
    Base.metadata,
    Column("tariff_id", Integer, ForeignKey("tariffs.id", ondelete="CASCADE"), primary_key=True),
    Column("package_id", Integer, ForeignKey("packages.id", ondelete="CASCADE"), primary_key=True),
)

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

group_channels = Table(
    "group_channels",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("channel_id", Integer, ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True),
)


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class Group(Base, TimestampMixin):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, index=True)

    channels: Mapped[list["Channel"]] = relationship(
        "Channel",
        secondary=group_channels,
        back_populates="groups",
        lazy="selectin",
    )


class Channel(Base, TimestampMixin):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    stream_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    tvg_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    catchup_days: Mapped[int | None] = mapped_column(nullable=True)
    tvg_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tvg_logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_number: Mapped[int | None] = mapped_column(nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0, index=True)
    sync_status: Mapped[SyncStatus] = mapped_column(Enum(SyncStatus, native_enum=False), default=SyncStatus.SYNCED, index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)

    groups: Mapped[list["Group"]] = relationship(
        "Group",
        secondary=group_channels,
        back_populates="channels",
        lazy="selectin",
    )
    packages: Mapped[list["Package"]] = relationship("Package", secondary=package_channels, back_populates="channels", lazy="selectin")


class Package(Base, TimestampMixin):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    channels: Mapped[list["Channel"]] = relationship("Channel", secondary=package_channels, back_populates="packages", lazy="selectin")
    tariffs: Mapped[list["Tariff"]] = relationship("Tariff", secondary=tariff_packages, back_populates="packages", lazy="selectin")


class Tariff(Base, TimestampMixin):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    packages: Mapped[list["Package"]] = relationship("Package", secondary=tariff_packages, back_populates="tariffs", lazy="selectin")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    agreement_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus, native_enum=False), default=UserStatus.ENABLED, index=True)
    max_sessions: Mapped[int] = mapped_column(default=1, nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    auth_token_id: Mapped[int | None] = mapped_column(nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(nullable=True)

    tariffs: Mapped[list["Tariff"]] = relationship("Tariff", secondary=user_tariffs, lazy="selectin")
    packages: Mapped[list["Package"]] = relationship("Package", secondary=user_packages, lazy="selectin")
    channels: Mapped[list["Channel"]] = relationship("Channel", secondary=user_channels, lazy="selectin")
