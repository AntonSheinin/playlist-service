import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.flussonic import FlussonicClient
from app.models import Channel, SyncStatus

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of channel synchronization."""

    total: int
    new: int
    updated: int
    orphaned: int


class ChannelSyncService:
    """Service for synchronizing channels from Flussonic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.flussonic = FlussonicClient()

    async def sync(self) -> SyncResult:
        """
        Synchronize channels from Flussonic.

        Process:
        1. Fetch all streams from Flussonic API
        2. For each stream:
           - If exists in DB: update Flussonic fields only
           - If not in DB: create new channel
        3. Mark channels not in Flussonic as orphaned
        """
        logger.info("Starting channel sync from Flussonic")

        # Fetch streams from Flussonic
        streams = await self.flussonic.get_streams()
        stream_names = {s.name for s in streams}

        now = datetime.utcnow()
        new_count = 0
        updated_count = 0

        # Process each stream from Flussonic
        for stream in streams:
            stmt = select(Channel).where(Channel.stream_name == stream.name)
            result = await self.db.execute(stmt)
            channel = result.scalar_one_or_none()

            if channel is None:
                # Create new channel
                channel = Channel(
                    stream_name=stream.name,
                    tvg_name=stream.title,
                    display_name=stream.title,
                    catchup_days=stream.dvr,
                    sync_status=SyncStatus.SYNCED,
                    last_seen_at=now,
                )
                self.db.add(channel)
                new_count += 1
            else:
                # Update Flussonic fields only (preserve UI-managed fields)
                channel.tvg_name = stream.title
                channel.display_name = stream.title
                channel.catchup_days = stream.dvr
                channel.sync_status = SyncStatus.SYNCED
                channel.last_seen_at = now
                updated_count += 1

        # Mark orphaned channels
        stmt = select(Channel).where(Channel.stream_name.notin_(stream_names))
        result = await self.db.execute(stmt)
        orphaned_channels = result.scalars().all()

        orphaned_count = 0
        for channel in orphaned_channels:
            if channel.sync_status != SyncStatus.ORPHANED:
                channel.sync_status = SyncStatus.ORPHANED
                orphaned_count += 1

        await self.db.flush()

        logger.info(
            "Channel sync complete: total=%d, new=%d, updated=%d, orphaned=%d",
            len(streams), new_count, updated_count, orphaned_count
        )

        return SyncResult(
            total=len(streams),
            new=new_count,
            updated=updated_count,
            orphaned=orphaned_count,
        )
