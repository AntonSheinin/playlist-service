import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.package import Package


class SyncStatus(str, enum.Enum):
    SYNCED = "synced"
    ORPHANED = "orphaned"


package_channels = Table(
    "package_channels",
    Base.metadata,
    Column("package_id", Integer, ForeignKey("packages.id", ondelete="CASCADE"), primary_key=True),
    Column("channel_id", Integer, ForeignKey("channels.id", ondelete="CASCADE"), primary_key=True),
)


class Channel(Base, TimestampMixin):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Flussonic fields (synced from external source)
    stream_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    tvg_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stream_base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    catchup_days: Mapped[int | None] = mapped_column(nullable=True)

    # UI-managed fields
    tvg_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tvg_logo: Mapped[str | None] = mapped_column(Text, nullable=True)  # Base64 encoded
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True,
    )
    sort_order: Mapped[int] = mapped_column(default=0, index=True)

    # Sync status
    sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, native_enum=False),
        default=SyncStatus.SYNCED,
        index=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    group: Mapped["Group | None"] = relationship("Group", back_populates="channels")
    packages: Mapped[list["Package"]] = relationship(
        "Package",
        secondary=package_channels,
        back_populates="channels",
        lazy="selectin",
    )
