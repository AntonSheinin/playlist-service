import logging
from typing import Any

import httpx
from pydantic import BaseModel

from app.config import MINUTES_PER_DAY, SECONDS_PER_DAY, get_settings
from app.exceptions import FlussonicError

logger = logging.getLogger(__name__)

# Threshold for distinguishing minutes from days in DVR depth
DVR_DEPTH_MINUTES_THRESHOLD = 365
V3_READINESS_ENDPOINT = "/streamer/api/v3/monitoring/readiness"
V3_LIVENESS_ENDPOINT = "/streamer/api/v3/monitoring/liveness"
V3_STATS_ENDPOINT = "/streamer/api/v3/config/stats"


class FlussonicStream(BaseModel):
    """Represents a stream from Flussonic API."""

    name: str  # stream_name (unique identifier)
    title: str | None = None  # display_name
    dvr: int | None = None  # catchup_days


class FlussonicClient:
    """Client for Flussonic Media Server API."""

    # API endpoints in order of preference (newest first)
    API_ENDPOINTS = [
        "/streamer/api/v3/streams",
        "/flussonic/api/media",
        "/erlyvideo/api/streams",
    ]

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.flussonic_url.rstrip("/")
        self.username = settings.flussonic_username
        self.password = settings.flussonic_password
        self.timeout = settings.flussonic_timeout
        self.page_limit = settings.flussonic_page_limit

    async def get_dashboard_stats(self) -> dict[str, int | str | None]:
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

        return {
            "health": health,
            "incoming_kbit": self._as_int(stats.get("input_kbit")),
            "outgoing_kbit": self._as_int(stats.get("output_kbit")),
            "total_clients": self._as_int(stats.get("total_clients")),
            "total_sources": total_sources,
            "good_sources": good_sources,
            "broken_sources": broken_sources,
        }

    async def get_streams(self) -> list[FlussonicStream]:
        """
        Fetch all streams from Flussonic.

        Tries multiple API endpoints for compatibility with different Flussonic versions.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            auth = httpx.BasicAuth(self.username, self.password)

            # Try API v3 first with pagination
            streams = await self._try_v3_api(client, auth)
            if streams is not None:
                return streams

            # Try legacy APIs
            for endpoint in self.API_ENDPOINTS[1:]:
                streams = await self._try_legacy_api(client, auth, endpoint)
                if streams is not None:
                    return streams

            raise FlussonicError("Failed to fetch streams from any Flussonic API endpoint")

    async def _check_v3_health(
        self, client: httpx.AsyncClient, auth: httpx.BasicAuth
    ) -> bool:
        """Check Flussonic health endpoints. Returns True if any probe succeeds."""
        endpoints = [V3_READINESS_ENDPOINT, V3_LIVENESS_ENDPOINT]

        for endpoint in endpoints:
            url = f"{self.base_url}{endpoint}"
            try:
                response = await client.get(url, auth=auth)
                if response.status_code == 200:
                    return True
                logger.debug(
                    "Flussonic health probe %s returned status %d",
                    endpoint,
                    response.status_code,
                )
            except httpx.TimeoutException:
                logger.warning("Timeout during Flussonic health probe at %s", url)
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

    async def _try_v3_api(
        self, client: httpx.AsyncClient, auth: httpx.BasicAuth
    ) -> list[FlussonicStream] | None:
        """Try fetching streams from API v3 with pagination."""
        endpoint = self.API_ENDPOINTS[0]
        url = f"{self.base_url}{endpoint}"

        try:
            all_streams: list[FlussonicStream] = []
            cursor = None

            while True:
                params: dict[str, int | str] = {"limit": self.page_limit}
                if cursor:
                    params["cursor"] = cursor

                response = await client.get(url, auth=auth, params=params)

                if response.status_code != 200:
                    logger.debug(
                        "Flussonic API v3 returned status %d", response.status_code
                    )
                    return None

                data = response.json()
                streams = self._parse_v3_response(data)
                all_streams.extend(streams)

                cursor = data.get("next") if isinstance(data, dict) else None
                if not cursor:
                    break

            logger.info("Fetched %d streams from Flussonic API v3", len(all_streams))
            return all_streams if all_streams else None

        except httpx.TimeoutException:
            logger.warning("Timeout connecting to Flussonic API v3 at %s", url)
            return None
        except httpx.RequestError as e:
            logger.debug("Failed to connect to Flussonic API v3: %s", e)
            return None

    async def _try_legacy_api(
        self, client: httpx.AsyncClient, auth: httpx.BasicAuth, endpoint: str
    ) -> list[FlussonicStream] | None:
        """Try fetching streams from a legacy API endpoint."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = await client.get(url, auth=auth)

            if response.status_code == 200:
                streams = self._parse_legacy_response(response.json())
                logger.info("Fetched %d streams from Flussonic %s", len(streams), endpoint)
                return streams

            logger.debug("Flussonic %s returned status %d", endpoint, response.status_code)
            return None

        except httpx.TimeoutException:
            logger.warning("Timeout connecting to Flussonic at %s", url)
            return None
        except httpx.RequestError as e:
            logger.debug("Failed to connect to Flussonic %s: %s", endpoint, e)
            return None

    def _parse_v3_response(self, data: dict | list) -> list[FlussonicStream]:
        """Parse response from Flussonic API v3."""
        streams = []

        # Handle different response formats
        if isinstance(data, dict):
            # Could be {"streams": [...]} or direct stream objects
            if "streams" in data:
                items = data["streams"]
            elif "items" in data:
                items = data["items"]
            else:
                # Direct object mapping {name: stream_config}
                items = [{"name": k, **v} for k, v in data.items() if isinstance(v, dict)]
        else:
            items = data

        for item in items:
            if isinstance(item, dict):
                stream = FlussonicStream(
                    name=item.get("name", item.get("stream_name", "")),
                    title=item.get("title", item.get("display_name")),
                    dvr=self._extract_dvr_days(item),
                )
                if stream.name:
                    streams.append(stream)

        return streams

    def _parse_legacy_response(self, data: dict | list) -> list[FlussonicStream]:
        """Parse response from legacy Flussonic API."""
        streams = []

        if isinstance(data, dict):
            # Handle {name: config} format
            for name, config in data.items():
                if isinstance(config, dict):
                    stream = FlussonicStream(
                        name=name,
                        title=config.get("title", config.get("display_name")),
                        dvr=self._extract_dvr_days(config),
                    )
                    streams.append(stream)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    stream = FlussonicStream(
                        name=item.get("name", ""),
                        title=item.get("title"),
                        dvr=self._extract_dvr_days(item),
                    )
                    if stream.name:
                        streams.append(stream)

        return streams

    def _extract_dvr_days(self, item: dict) -> int | None:
        """Extract DVR days from various possible field names."""
        for field in ["dvr", "dvr_days", "catchup_days", "archive_depth"]:
            if field in item:
                value = item[field]
                if isinstance(value, int):
                    return value
                if isinstance(value, dict):
                    # API v3 format: {"dvr": {"expiration": 1209600}} (seconds)
                    if "expiration" in value:
                        expiration = value["expiration"]
                        if isinstance(expiration, int) and expiration > 0:
                            return expiration // SECONDS_PER_DAY
                    # Alternative format: {"dvr": {"depth": 14}}
                    if "depth" in value:
                        depth = value["depth"]
                        if isinstance(depth, int):
                            if depth > DVR_DEPTH_MINUTES_THRESHOLD:
                                return depth // MINUTES_PER_DAY
                            return depth
        return None
