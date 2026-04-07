import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.stream_provider import get_stream_provider
from app.models import Channel, StreamSource, SyncStatus

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of channel synchronization."""

    source: StreamSource
    total: int
    new: int
    updated: int
    orphaned: int


class ChannelSyncService:
    """Service for synchronizing channels from a stream provider."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sync(self, source: StreamSource) -> SyncResult:
        """
        Synchronize channels from a stream provider.

        Process:
        1. Fetch all streams from the provider API
        2. For each stream:
           - If exists in DB: update provider-managed fields only
           - If not in DB: create new channel
        3. Mark channels missing from the provider as orphaned within that provider only
        """
        provider = get_stream_provider(source)
        logger.info("Starting channel sync from %s", source.value)

        streams = await provider.get_streams()
        stream_names = {s.name for s in streams}

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        new_count = 0
        updated_count = 0

        for stream in streams:
            stmt = select(Channel).where(
                Channel.source == source,
                Channel.stream_name == stream.name,
            )
            result = await self.db.execute(stmt)
            channel = result.scalar_one_or_none()

            if channel is None:
                channel = Channel(
                    source=source,
                    stream_name=stream.name,
                    tvg_name=stream.title,
                    display_name=stream.title,
                    catchup_days=stream.catchup_days,
                    sync_status=SyncStatus.SYNCED,
                    last_seen_at=now,
                )
                self.db.add(channel)
                new_count += 1
            else:
                channel.tvg_name = stream.title
                channel.display_name = stream.title
                channel.catchup_days = stream.catchup_days
                channel.sync_status = SyncStatus.SYNCED
                channel.last_seen_at = now
                updated_count += 1

        stmt = select(Channel).where(Channel.source == source)
        if stream_names:
            stmt = stmt.where(Channel.stream_name.notin_(stream_names))
        result = await self.db.execute(stmt)
        orphaned_channels = result.scalars().all()

        orphaned_count = 0
        for channel in orphaned_channels:
            if channel.sync_status != SyncStatus.ORPHANED:
                channel.sync_status = SyncStatus.ORPHANED
                orphaned_count += 1

        await self.db.flush()

        logger.info(
            "Channel sync complete for %s: total=%d, new=%d, updated=%d, orphaned=%d",
            source.value,
            len(streams),
            new_count,
            updated_count,
            orphaned_count,
        )

        return SyncResult(
            source=source,
            total=len(streams),
            new=new_count,
            updated=updated_count,
            orphaned=orphaned_count,
        )
