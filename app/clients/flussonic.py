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
class _ActiveSourceCountersCacheEntry:
    expires_at: float
    counters: ProviderActiveSourceCounters


_active_source_counters_cache: dict[str, _ActiveSourceCountersCacheEntry] = {}
_active_source_counters_cache_lock = asyncio.Lock()


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
            active_source_counters = await self._get_cached_active_source_counters(client, auth)

        total_sources = self._as_int(stats.get("total_streams"))
        good_sources = self._as_int(stats.get("online_streams"))
        broken_sources: int | None = None
        if total_sources is not None and good_sources is not None:
            broken_sources = max(total_sources - good_sources, 0)

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
            active_source_counters=active_source_counters,
        )

    async def get_streams(self) -> list[ProviderStream]:
        """
        Fetch all streams from Flussonic V3.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            auth = httpx.BasicAuth(self.username, self.password)
            items = await self._get_v3_stream_items(client, auth)

        streams: list[ProviderStream] = []
        for item in items:
            stream = self._parse_stream_item(item)
            if stream is not None:
                streams.append(stream)
        return streams

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
        url = f"{self.base_url}{V3_STATS_ENDPOINT}"

        try:
            response = await client.get(url, auth=auth)
            if response.status_code != 200:
                logger.error(
                    "Flussonic stats endpoint returned status %d: %s",
                    response.status_code,
                    response.text,
                )
                raise FlussonicError(
                    f"Failed to fetch Flussonic stats: {response.status_code}"
                )

            payload = response.json()
            if not isinstance(payload, dict):
                raise FlussonicError("Unexpected Flussonic stats response format")
            return payload

        except httpx.TimeoutException:
            logger.error("Timeout connecting to Flussonic stats endpoint at %s", url)
            raise FlussonicError(
                f"Timeout connecting to Flussonic stats endpoint at {url}"
            ) from None
        except httpx.RequestError as e:
            logger.error("Failed to connect to Flussonic stats endpoint: %s", e)
            raise FlussonicError(f"Failed to connect to Flussonic stats endpoint: {e}") from e

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
        url = f"{self.base_url}{self.STREAMS_ENDPOINT}"

        try:
            all_items: list[dict[str, Any]] = []
            cursor = None

            while True:
                params: dict[str, int | str] = {"limit": self.page_limit}
                if cursor:
                    params["cursor"] = cursor

                response = await client.get(url, auth=auth, params=params)

                if response.status_code != 200:
                    raise FlussonicError(
                        f"Failed to fetch Flussonic streams: {response.status_code}"
                    )

                data = response.json()
                items = self._extract_v3_items(data)
                all_items.extend(items)

                cursor = data.get("next")
                if not cursor:
                    break

            logger.info("Fetched %d streams from Flussonic API v3", len(all_items))
            return all_items
        except httpx.TimeoutException:
            raise FlussonicError(f"Timeout connecting to Flussonic API v3 at {url}") from None
        except httpx.RequestError as e:
            raise FlussonicError(f"Failed to connect to Flussonic API v3: {e}") from e

    async def _get_cached_active_source_counters(
        self, client: httpx.AsyncClient, auth: httpx.BasicAuth
    ) -> ProviderActiveSourceCounters:
        cache_key = self.base_url
        now = time.monotonic()
        cached = _active_source_counters_cache.get(cache_key)
        if cached is not None and cached.expires_at > now:
            return cached.counters

        async with _active_source_counters_cache_lock:
            now = time.monotonic()
            cached = _active_source_counters_cache.get(cache_key)
            if cached is not None and cached.expires_at > now:
                return cached.counters

            items = await self._get_v3_stream_items(client, auth)
            counters = self._count_active_source_counters(items)
            _active_source_counters_cache[cache_key] = _ActiveSourceCountersCacheEntry(
                expires_at=now + ACTIVE_SOURCE_COUNTERS_CACHE_TTL_SECONDS,
                counters=counters,
            )
            return counters

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

        active_url = self._find_input_url(configured_inputs, require_active=True)
        if active_url is not None:
            return active_url

        return None

    def _find_input_url(
        self, inputs: list[dict[str, Any]], *, require_active: bool
    ) -> str | None:
        for input_item in inputs:
            input_stats = input_item.get("stats")
            is_active = False
            if isinstance(input_stats, dict):
                active = input_stats.get("active")
                if isinstance(active, bool):
                    is_active = active

            if require_active and not is_active:
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
