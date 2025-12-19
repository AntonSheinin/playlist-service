import logging

import httpx
from pydantic import BaseModel

from app.config import MINUTES_PER_DAY, SECONDS_PER_DAY, get_settings
from app.exceptions import FlussonicError

logger = logging.getLogger(__name__)

# Threshold for distinguishing minutes from days in DVR depth
DVR_DEPTH_MINUTES_THRESHOLD = 365


class FlussonicStream(BaseModel):
    """Represents a stream from Flussonic API."""

    name: str  # stream_name (unique identifier)
    title: str | None = None  # display_name
    dvr: int | None = None  # catchup_days
    static: bool = True


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
                    static=item.get("static", True),
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
                        static=config.get("static", True),
                    )
                    streams.append(stream)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    stream = FlussonicStream(
                        name=item.get("name", ""),
                        title=item.get("title"),
                        dvr=self._extract_dvr_days(item),
                        static=item.get("static", True),
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

    def get_stream_url(self, stream_name: str) -> str:
        """Get the base URL for a stream."""
        return f"{self.base_url}/{stream_name}"
