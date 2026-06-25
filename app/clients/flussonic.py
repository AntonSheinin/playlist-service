import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import SECONDS_PER_DAY, get_settings
from app.clients.stream_provider import (
    ProviderActiveSourceCounters,
    ProviderDashboardStats,
    ProviderStream,
)
from app.exceptions import FlussonicError
from app.models import StreamSource

logger = logging.getLogger(__name__)

V3_READINESS_ENDPOINT = "/streamer/api/v3/monitoring/readiness"
V3_STATS_ENDPOINT = "/streamer/api/v3/config/stats"
ONLINE24_HOST_MARKER = "online24"
RESTREAM_HOST = "restream.pw"
RESTREAM_IP = "185.96.80.44"
ACTIVE_SOURCE_COUNTERS_CACHE_TTL_SECONDS = 30.0


@dataclass(frozen=True)
class _StreamDerivedStats:
    total_sources: int
    broken_sources: int
    active_source_counters: ProviderActiveSourceCounters


@dataclass(frozen=True)
class _StreamStatsCacheEntry:
    expires_at: float
    stats: _StreamDerivedStats


_stream_stats_cache: dict[str, _StreamStatsCacheEntry] = {}
_stream_stats_cache_lock = asyncio.Lock()


class FlussonicClient:
    """Client for Flussonic Media Server API."""

    source = StreamSource.FLUSSONIC
    STREAMS_ENDPOINT = "/streamer/api/v3/streams"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.flussonic_url or not settings.flussonic_username or not settings.flussonic_password:
            raise FlussonicError("Not configured")

        self.base_url = settings.flussonic_url.rstrip("/")
        self.username = settings.flussonic_username
        self.password = settings.flussonic_password
        self.timeout = settings.flussonic_timeout
        self.page_limit = settings.flussonic_page_limit

    def build_stream_url(self, stream_name: str, token: str) -> str:
        return f"{self.base_url}/{stream_name}/video.m3u8?token={token}"

    async def get_dashboard_stats(self) -> ProviderDashboardStats:
        """
        Fetch Flussonic dashboard stats.

        Includes health status, incoming/outgoing traffic and source counters.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            auth = httpx.BasicAuth(self.username, self.password)
            health_probe_ok = await self._check_v3_health(client, auth)
            stats = await self._get_v3_server_stats(client, auth)
            stream_stats = await self._get_cached_stream_stats(client, auth)

        total_sources = stream_stats.total_sources
        broken_sources = stream_stats.broken_sources
        good_sources = max(total_sources - broken_sources, 0)

        streamer_status = stats.get("streamer_status")
        health = "up"
        if not health_probe_ok:
            health = "down"
        elif isinstance(streamer_status, str) and streamer_status != "running":
            health = "degraded"

        return ProviderDashboardStats(
            health=health,
            incoming_kbit=self._as_int(stats.get("input_kbit")),
            outgoing_kbit=self._as_int(stats.get("output_kbit")),
            total_clients=self._as_int(stats.get("total_clients")),
            total_sources=total_sources,
            good_sources=good_sources,
            broken_sources=broken_sources,
            active_source_counters=stream_stats.active_source_counters,
        )

    async def get_streams(self) -> list[ProviderStream]:
        """
        Fetch all streams from Flussonic V3.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            auth = httpx.BasicAuth(self.username, self.password)
            items = await self._get_v3_stream_items(client, auth)

        return [
            stream
            for item in items
            if (stream := self._parse_stream_item(item)) is not None
        ]

    async def _check_v3_health(
        self, client: httpx.AsyncClient, auth: httpx.BasicAuth
    ) -> bool:
        """Check the Flussonic V3 readiness endpoint."""
        url = f"{self.base_url}{V3_READINESS_ENDPOINT}"
        try:
            response = await client.get(url, auth=auth)
            return response.status_code == 200
        except httpx.TimeoutException:
            logger.warning("Timeout during Flussonic health probe at %s", url)
            return False
        except httpx.RequestError as e:
            logger.debug("Flussonic health probe failed at %s: %s", url, e)
            return False

    async def _get_v3_server_stats(
        self, client: httpx.AsyncClient, auth: httpx.BasicAuth
    ) -> dict[str, Any]:
        """Fetch server stats from Flussonic v3 API."""
        return await self._get_v3_json(
            client,
            auth,
            V3_STATS_ENDPOINT,
            operation="fetch Flussonic stats",
            response_description="Flussonic stats",
        )

    def _as_int(self, value: Any) -> int | None:
        """Convert API value to int when possible."""
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return None
        return None

    async def _get_v3_stream_items(
        self, client: httpx.AsyncClient, auth: httpx.BasicAuth
    ) -> list[dict[str, Any]]:
        """Fetch raw stream items from Flussonic API v3 with pagination."""
        all_items: list[dict[str, Any]] = []
        cursor = None

        while True:
            params: dict[str, int | str] = {"limit": self.page_limit}
            if cursor:
                params["cursor"] = cursor

            data = await self._get_v3_json(
                client,
                auth,
                self.STREAMS_ENDPOINT,
                params=params,
                operation="fetch Flussonic streams",
                response_description="Flussonic streams",
            )
            all_items.extend(self._extract_v3_items(data))

            cursor = data.get("next")
            if not cursor:
                break

        logger.info("Fetched %d streams from Flussonic API v3", len(all_items))
        return all_items

    async def _get_v3_json(
        self,
        client: httpx.AsyncClient,
        auth: httpx.BasicAuth,
        path: str,
        *,
        operation: str,
        response_description: str,
        params: dict[str, int | str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = await client.get(url, auth=auth, params=params)
            if response.status_code != 200:
                logger.error(
                    "Failed to %s: %d - %s",
                    operation,
                    response.status_code,
                    response.text,
                )
                raise FlussonicError(f"Failed to {operation}: {response.status_code}")

            payload = response.json()
            if isinstance(payload, dict):
                return payload
            raise FlussonicError(f"Unexpected {response_description} response format")
        except httpx.TimeoutException:
            logger.error("Timeout during %s at %s", operation, url)
            raise FlussonicError(f"Timeout during {operation} at {url}") from None
        except httpx.RequestError as e:
            logger.error("Connection error during %s: %s", operation, e)
            raise FlussonicError(f"Failed to {operation}: {e}") from e

    async def _get_cached_stream_stats(
        self, client: httpx.AsyncClient, auth: httpx.BasicAuth
    ) -> _StreamDerivedStats:
        cache_key = self.base_url
        now = time.monotonic()
        cached = _stream_stats_cache.get(cache_key)
        if cached is not None and cached.expires_at > now:
            return cached.stats

        async with _stream_stats_cache_lock:
            now = time.monotonic()
            cached = _stream_stats_cache.get(cache_key)
            if cached is not None and cached.expires_at > now:
                return cached.stats

            items = await self._get_v3_stream_items(client, auth)
            stream_stats = _StreamDerivedStats(
                total_sources=len(items),
                broken_sources=self._count_broken_sources(items),
                active_source_counters=self._count_active_source_counters(items),
            )
            _stream_stats_cache[cache_key] = _StreamStatsCacheEntry(
                expires_at=now + ACTIVE_SOURCE_COUNTERS_CACHE_TTL_SECONDS,
                stats=stream_stats,
            )
            return stream_stats

    def _extract_v3_items(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract stream items from a Flussonic V3 response page."""
        items = data.get("streams")
        if not isinstance(items, list):
            raise FlussonicError("Unexpected Flussonic streams response format")
        return [item for item in items if isinstance(item, dict)]

    def _parse_stream_item(self, item: dict[str, Any]) -> ProviderStream | None:
        name = item.get("name")
        if not isinstance(name, str) or not name:
            return None

        title = item.get("title")
        return ProviderStream(
            name=name,
            title=title if isinstance(title, str) else None,
            catchup_days=self._extract_dvr_days(item),
        )

    def _count_active_source_counters(
        self, items: list[dict[str, Any]]
    ) -> ProviderActiveSourceCounters:
        online24 = 0
        restream = 0
        other = 0

        for item in items:
            input_url = self._get_active_input_url(item)
            if input_url is None:
                continue

            source_group = self._classify_input_url(input_url)
            if source_group == "online24":
                online24 += 1
            elif source_group == "restream":
                restream += 1
            else:
                other += 1

        return ProviderActiveSourceCounters(
            online24=online24,
            restream=restream,
            other=other,
        )

    def _count_broken_sources(self, items: list[dict[str, Any]]) -> int:
        return sum(
            1
            for item in items
            if isinstance(item.get("stats"), dict)
            and item["stats"].get("status") == "error"
        )

    def _get_active_input_url(self, item: dict[str, Any]) -> str | None:
        inputs = item.get("inputs")
        if not isinstance(inputs, list):
            return None

        configured_inputs = [
            input_item for input_item in inputs if isinstance(input_item, dict)
        ]
        configured_inputs.sort(
            key=lambda input_item: self._as_int(input_item.get("priority")) or 0
        )

        for input_item in configured_inputs:
            input_stats = input_item.get("stats")
            if not isinstance(input_stats, dict) or input_stats.get("active") is not True:
                continue

            url = input_item.get("url")
            if isinstance(url, str) and url.strip():
                return url.strip()

        return None

    def _classify_input_url(self, value: str) -> str:
        hostname = urlparse(value).hostname or ""
        normalized = hostname.strip().lower()

        if ONLINE24_HOST_MARKER in normalized:
            return "online24"
        if normalized == RESTREAM_IP or normalized == RESTREAM_HOST or normalized.endswith(
            f".{RESTREAM_HOST}"
        ):
            return "restream"
        return "other"

    def _extract_dvr_days(self, item: dict) -> int | None:
        """Extract DVR days from the Flussonic V3 dvr.expiration field."""
        value = item.get("dvr")
        if isinstance(value, dict):
            expiration = value.get("expiration")
            if isinstance(expiration, int) and expiration > 0:
                return expiration // SECONDS_PER_DAY
        return None
