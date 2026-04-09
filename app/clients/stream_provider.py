from dataclasses import dataclass
from typing import Protocol

from app.models import StreamSource


@dataclass(frozen=True)
class ProviderStream:
    name: str
    title: str | None = None
    catchup_days: int | None = None


@dataclass(frozen=True)
class ProviderActiveSourceCounters:
    online24: int
    restream: int
    other: int


@dataclass(frozen=True)
class ProviderDashboardStats:
    health: str
    incoming_kbit: int | None = None
    outgoing_kbit: int | None = None
    total_clients: int | None = None
    total_sources: int | None = None
    good_sources: int | None = None
    broken_sources: int | None = None
    active_source_counters: ProviderActiveSourceCounters | None = None
    error: str | None = None


class StreamProvider(Protocol):
    source: StreamSource

    async def get_streams(self) -> list[ProviderStream]:
        ...

    async def get_dashboard_stats(self) -> ProviderDashboardStats:
        ...

    def build_stream_url(self, stream_name: str, token: str) -> str:
        ...


def get_stream_provider(source: StreamSource) -> StreamProvider:
    if source == StreamSource.FLUSSONIC:
        from app.clients.flussonic import FlussonicClient

        return FlussonicClient()
    if source == StreamSource.NIMBLE:
        from app.clients.nimble import NimbleClient

        return NimbleClient()
    raise ValueError(f"Unsupported stream source: {source}")
