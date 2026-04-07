import logging
from typing import Any

import httpx

from app.config import SECONDS_PER_DAY, get_settings
from app.clients.stream_provider import ProviderDashboardStats, ProviderStream
from app.exceptions import FlussonicError
from app.models import StreamSource

logger = logging.getLogger(__name__)

V3_READINESS_ENDPOINT = "/streamer/api/v3/monitoring/readiness"
V3_STATS_ENDPOINT = "/streamer/api/v3/config/stats"


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
        )

    async def get_streams(self) -> list[ProviderStream]:
        """
        Fetch all streams from Flussonic V3.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            auth = httpx.BasicAuth(self.username, self.password)
            return await self._get_v3_streams(client, auth)

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

    async def _get_v3_streams(
        self, client: httpx.AsyncClient, auth: httpx.BasicAuth
    ) -> list[ProviderStream]:
        """Fetch streams from Flussonic API v3 with pagination."""
        url = f"{self.base_url}{self.STREAMS_ENDPOINT}"

        try:
            all_streams: list[ProviderStream] = []
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
                streams = self._parse_v3_response(data)
                all_streams.extend(streams)

                cursor = data.get("next")
                if not cursor:
                    break

            logger.info("Fetched %d streams from Flussonic API v3", len(all_streams))
            return all_streams
        except httpx.TimeoutException:
            raise FlussonicError(f"Timeout connecting to Flussonic API v3 at {url}") from None
        except httpx.RequestError as e:
            raise FlussonicError(f"Failed to connect to Flussonic API v3: {e}") from e

    def _parse_v3_response(self, data: dict[str, Any]) -> list[ProviderStream]:
        """Parse response from Flussonic API v3."""
        items = data.get("items")
        if not isinstance(items, list):
            raise FlussonicError("Unexpected Flussonic streams response format")

        streams: list[ProviderStream] = []
        for item in items:
            if isinstance(item, dict):
                name = item.get("name")
                title = item.get("title")
                stream = ProviderStream(
                    name=name if isinstance(name, str) else "",
                    title=title if isinstance(title, str) else None,
                    catchup_days=self._extract_dvr_days(item),
                )
                if stream.name:
                    streams.append(stream)

        return streams

    def _extract_dvr_days(self, item: dict) -> int | None:
        """Extract DVR days from the Flussonic V3 dvr.expiration field."""
        value = item.get("dvr")
        if isinstance(value, dict):
            expiration = value.get("expiration")
            if isinstance(expiration, int) and expiration > 0:
                return expiration // SECONDS_PER_DAY
        return None
